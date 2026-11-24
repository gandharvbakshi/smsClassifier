package com.smsclassifier.app.data

import android.content.ContentResolver
import android.net.Uri
import android.provider.Telephony
import androidx.room.withTransaction
import com.smsclassifier.app.util.AppLog
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

// Serialize provider imports with bulk deletion so an open import cursor cannot restore a deleted row.
internal val smsImportDeletionMutex = Mutex()

internal data class SmsDeletionIdentity(
    val id: Long,
    val threadId: Long,
    val sender: String,
    val body: String,
    val timestamp: Long,
    val type: Int,
    val providerId: Long?
) {
    constructor(message: MessageEntity) : this(
        message.id, message.threadId, message.sender, message.body,
        message.ts, message.type, message.sourceProviderId
    )
}

internal data class BulkSmsDeletePlan(
    val conversations: Boolean,
    val messages: List<SmsDeletionIdentity>,
    val legacyProviderIds: Map<Long, Long?> = emptyMap()
) {
    val conversationCount: Int get() = messages.map { it.threadId }.distinct().size
}

internal data class BulkSmsDeleteResult(val removed: Int, val alreadyAbsent: Int, val failed: Int)

internal class BulkSmsDeletion(
    private val database: AppDatabase,
    private val smsUri: Uri = Telephony.Sms.CONTENT_URI
) {
    private val dao = database.messageDao()

    suspend fun prepare(
        resolver: ContentResolver,
        selectedRows: Map<Long, SmsDeletionIdentity?>,
        conversations: Boolean
    ): BulkSmsDeletePlan =
        withContext(Dispatchers.IO) {
            val messages = database.withTransaction {
                // Keep the number of bind parameters below SQLite's limit on supported versions.
                selectedRows.keys.chunked(400).flatMap { batch ->
                    if (conversations) dao.getByThreadIds(batch) else dao.getByIds(batch)
                }.map(::SmsDeletionIdentity).filter { conversations || it == selectedRows[it.id] }
            }
            val legacyProviderIds = mutableMapOf<Long, Long?>()
            for (message in messages.filter { it.providerId == null }) {
                ensureActive()
                try {
                    val (selection, args) = providerFingerprint(message)
                    val matches = providerIds(resolver, selection, args)
                    if (matches.size <= 1) legacyProviderIds[message.id] = matches.singleOrNull()
                } catch (e: CancellationException) {
                    throw e
                } catch (_: Exception) {
                    // Leave an unverified legacy row out of the provider snapshot.
                }
            }
            BulkSmsDeletePlan(conversations, messages, legacyProviderIds)
        }

    suspend fun delete(resolver: ContentResolver, plan: BulkSmsDeletePlan): BulkSmsDeleteResult =
        withContext(Dispatchers.IO + NonCancellable) {
            smsImportDeletionMutex.withLock {
                val selected = plan.messages.associateBy { it.id }
                executeBulkSmsDelete(
                    plan = plan,
                    read = { dao.getById(it)?.let(::SmsDeletionIdentity) },
                    deleteProvider = { deleteProviderCopy(resolver, it, selected, plan.legacyProviderIds) },
                    deleteLocal = {
                        dao.deleteExact(it.id, it.threadId, it.sender, it.body, it.timestamp, it.type, it.providerId) == 1
                    },
                    onFailure = {
                        AppLog.w("BulkSmsDeletion", "A selected SMS could not be deleted (${it.javaClass.simpleName})")
                    }
                )
            }
        }

    private suspend fun deleteProviderCopy(
        resolver: ContentResolver,
        message: SmsDeletionIdentity,
        selected: Map<Long, SmsDeletionIdentity>,
        legacyProviderIds: Map<Long, Long?>
    ) {
        val (selection, args) = providerFingerprint(message)
        val matches = providerIds(resolver, selection, args)
        if (message.providerId == null) {
            // Do not adopt another provider row after the user has reviewed the selection.
            check(legacyProviderIds.containsKey(message.id))
            check(matches.isEmpty() || matches.single() == legacyProviderIds[message.id])
        }
        if (matches.isEmpty()) {
            // The stored or confirmed provider ID distinguishes absence from a changed identity.
            val providerId = message.providerId ?: legacyProviderIds[message.id]
            check(providerId == null || !providerIdExists(resolver, providerId))
            return
        }
        val providerId = matches.single()
        val aliases = dao.getProviderAliasIds(providerId, message.sender, message.body, message.timestamp, message.type)
        check(aliases.all { id ->
            id == message.id || (selected[id] != null && dao.getById(id)?.let(::SmsDeletionIdentity) == selected[id])
        })

        val changed = resolver.delete(
            smsUri,
            "${Telephony.Sms._ID} = ? AND ($selection)",
            arrayOf(providerId.toString()) + args
        )
        check(changed == 1 || (changed == 0 && !providerIdExists(resolver, providerId)))
    }

    private fun providerIdExists(resolver: ContentResolver, id: Long): Boolean =
        providerIds(resolver, "${Telephony.Sms._ID} = ?", arrayOf(id.toString())).isNotEmpty()

    private fun providerIds(
        resolver: ContentResolver,
        selection: String,
        args: Array<String>
    ): List<Long> = checkNotNull(
        resolver.query(smsUri, arrayOf(Telephony.Sms._ID), selection, args, null)
    ).use { cursor ->
        buildList {
            while (cursor.moveToNext()) add(cursor.getLong(0))
        }
    }
}

internal suspend fun executeBulkSmsDelete(
    plan: BulkSmsDeletePlan,
    read: suspend (Long) -> SmsDeletionIdentity?,
    deleteProvider: suspend (SmsDeletionIdentity) -> Unit,
    deleteLocal: suspend (SmsDeletionIdentity) -> Boolean,
    onFailure: (Exception) -> Unit = {}
): BulkSmsDeleteResult {
    var removed = 0
    var alreadyAbsent = 0
    var failed = 0
    for (expected in plan.messages) {
        try {
            val current = read(expected.id)
            when {
                current == null -> alreadyAbsent++
                current != expected || current.type == Telephony.Sms.MESSAGE_TYPE_OUTBOX -> failed++
                else -> {
                    deleteProvider(current)
                    when {
                        deleteLocal(current) -> removed++
                        read(current.id) == null -> alreadyAbsent++
                        else -> failed++
                    }
                }
            }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            onFailure(e)
            failed++
        }
    }
    return BulkSmsDeleteResult(removed, alreadyAbsent, failed)
}

internal fun providerFingerprint(message: SmsDeletionIdentity): Pair<String, Array<String>> {
    val address = Telephony.Sms.ADDRESS
    val addressClause = if (message.sender == "UNKNOWN") {
        "($address = ? OR $address IS NULL OR TRIM($address) = '')"
    } else {
        "$address = ?"
    }
    val hasOutgoingStatus = message.type == Telephony.Sms.MESSAGE_TYPE_SENT ||
        message.type == Telephony.Sms.MESSAGE_TYPE_FAILED
    val typeClause = if (hasOutgoingStatus) "${Telephony.Sms.TYPE} IN (?, ?)" else "${Telephony.Sms.TYPE} = ?"
    val clause = "$addressClause AND ${Telephony.Sms.BODY} = ? AND ${Telephony.Sms.DATE} = ? AND $typeClause"
    val args = arrayOf(message.sender, message.body, message.timestamp.toString(), message.type.toString()) +
        if (hasOutgoingStatus) {
            arrayOf(if (message.type == Telephony.Sms.MESSAGE_TYPE_SENT) "5" else "2")
        } else emptyArray()
    val providerId = message.providerId
    return if (providerId == null) clause to args else {
        "${Telephony.Sms._ID} = ? AND ($clause)" to (arrayOf(providerId.toString()) + args)
    }
}
