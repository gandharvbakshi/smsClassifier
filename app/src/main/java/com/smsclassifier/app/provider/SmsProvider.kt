package com.smsclassifier.app.provider

import android.content.ContentProvider
import android.content.ContentValues
import android.content.UriMatcher
import android.database.Cursor
import android.database.MatrixCursor
import android.net.Uri
import android.provider.Telephony
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.util.AppLog
import com.smsclassifier.app.util.ThreadUtils
import kotlinx.coroutines.runBlocking

/**
 * SMS ContentProvider that implements Android's SMS contract.
 * This allows other apps to read SMS messages using standard Android SMS URIs.
 */
class SmsProvider : ContentProvider() {

    private val uriMatcher = UriMatcher(UriMatcher.NO_MATCH)
    private var authority: String? = null

    override fun onCreate(): Boolean {
        val ctx = context ?: return false
        authority = "${ctx.packageName}.smsprovider"
        
        AppLog.d(TAG, "SmsProvider onCreate - Authority: $authority")
        
        // Handle standard Android SMS URIs through our custom authority
        // When app is default SMS handler, Android routes queries here
        uriMatcher.addURI(authority, "sms", SMS_ALL)
        uriMatcher.addURI(authority, "sms/#", SMS_SINGLE)
        uriMatcher.addURI(authority, "sms/inbox", SMS_INBOX)
        uriMatcher.addURI(authority, "sms/sent", SMS_SENT)
        uriMatcher.addURI(authority, "sms/draft", SMS_DRAFT)
        uriMatcher.addURI(authority, "sms/outbox", SMS_OUTBOX)
        
        // Also handle standard SMS URIs directly (Android may route these when we're default SMS handler)
        // Note: We can't register "sms" as authority (it's reserved), but Android should route content://sms/* to us
        // Try to handle if Android routes it with our authority or package name
        
        // Custom URIs (for backward compatibility)
        uriMatcher.addURI(authority, "messages", SMS_ALL)
        uriMatcher.addURI(authority, "messages/#", SMS_SINGLE)
        
        return true
    }

    override fun query(
        uri: Uri,
        projection: Array<out String>?,
        selection: String?,
        selectionArgs: Array<out String>?,
        sortOrder: String?
    ): Cursor? {
        val context = context ?: return null
        
        // Log all query attempts for debugging
        AppLog.d(TAG, "Query received - URI: $uri, Authority: ${uri.authority}, Path: ${uri.path}")
        AppLog.d(TAG, "Projection: ${projection?.joinToString()}, Selection: $selection")
        
        // Check if this is a standard SMS URI being routed to us
        // Android should route content://sms/* to our provider when we're default SMS handler
        // But it may come with different authority - try to handle both
        val uriAuthority = uri.authority
        val actualAuthority = authority
        
        // If URI has standard "sms" authority or matches our authority, handle it
        val isStandardSmsUri = uriAuthority == "sms" || uriAuthority?.contains("sms") == true
        val isOurAuthority = uriAuthority == actualAuthority || uriAuthority?.endsWith(".smsprovider") == true
        
        if (!isOurAuthority && !isStandardSmsUri) {
            AppLog.w(TAG, "Query with unrecognized authority: $uriAuthority (expected: $actualAuthority)")
            // Still try to handle if path matches SMS patterns
        }
        
        val dao = AppDatabase.getDatabase(context).messageDao()
        
        // Try to match URI pattern regardless of authority (Android may route with different authority)
        val pathSegments = uri.pathSegments
        val pathMatch = when {
            pathSegments.isEmpty() || (pathSegments.size == 1 && pathSegments[0] == "sms") -> SMS_ALL
            pathSegments.size == 2 && pathSegments[0] == "sms" && pathSegments[1] == "inbox" -> SMS_INBOX
            pathSegments.size == 2 && pathSegments[0] == "sms" && pathSegments[1] == "sent" -> SMS_SENT
            pathSegments.size == 2 && pathSegments[0] == "sms" && pathSegments[1] == "draft" -> SMS_DRAFT
            pathSegments.size == 2 && pathSegments[0] == "sms" && pathSegments[1] == "outbox" -> SMS_OUTBOX
            pathSegments.size == 2 && pathSegments[0] == "sms" -> {
                val id = pathSegments[1].toLongOrNull()
                if (id != null) SMS_SINGLE else SMS_ALL
            }
            else -> {
                // Try URI matcher with current authority
                uriMatcher.match(Uri.parse("content://$actualAuthority${uri.path}"))
            }
        }
        
        val messages = runBlocking {
            val allMessages = when (pathMatch) {
                SMS_ALL -> {
                    AppLog.d(TAG, "Query: SMS_ALL - returning all messages")
                    dao.getAllMessages()
                }
                SMS_INBOX -> {
                    AppLog.d(TAG, "Query: SMS_INBOX - returning inbox messages")
                    dao.getAllMessages().filter { it.type == 1 } // 1 = received
                }
                SMS_SENT -> {
                    AppLog.d(TAG, "Query: SMS_SENT - returning sent messages")
                    dao.getAllMessages().filter { it.type == 2 } // 2 = sent
                }
                SMS_DRAFT -> {
                    AppLog.d(TAG, "Query: SMS_DRAFT - returning draft messages")
                    dao.getAllMessages().filter { it.type == 3 } // 3 = draft
                }
                SMS_OUTBOX -> {
                    AppLog.d(TAG, "Query: SMS_OUTBOX - returning outbox messages")
                    dao.getAllMessages().filter { it.type == 4 } // 4 = outbox
                }
                SMS_SINGLE -> {
                    val id = uri.lastPathSegment?.toLongOrNull()
                    AppLog.d(TAG, "Query: SMS_SINGLE - message ID: $id")
                    if (id != null) {
                        dao.getById(id)?.let { listOf(it) } ?: emptyList()
                    } else {
                        emptyList()
                    }
                }
                else -> {
                    AppLog.w(TAG, "Query: Unmatched URI pattern - pathMatch: $pathMatch, URI: $uri")
                    // Try original URI matcher as fallback
                    when (uriMatcher.match(uri)) {
                        SMS_ALL -> dao.getAllMessages()
                        SMS_INBOX -> dao.getAllMessages().filter { it.type == 1 }
                        SMS_SENT -> dao.getAllMessages().filter { it.type == 2 }
                        SMS_DRAFT -> dao.getAllMessages().filter { it.type == 3 }
                        SMS_OUTBOX -> dao.getAllMessages().filter { it.type == 4 }
                        SMS_SINGLE -> {
                            val id = uri.lastPathSegment?.toLongOrNull()
                            if (id != null) {
                                dao.getById(id)?.let { listOf(it) } ?: emptyList()
                            } else {
                                emptyList()
                            }
                        }
                        else -> emptyList()
                    }
                }
            }
            
            // Sort messages by date descending (most recent first) - important for OTP extraction apps
            // OTP apps typically query the most recent messages first
            // Only sort if we have multiple messages (not SMS_SINGLE)
            if (pathMatch != SMS_SINGLE && allMessages.size > 1) {
                allMessages.sortedByDescending { it.ts }
            } else {
                allMessages
            }
        }

        val filteredMessages = applySelection(messages, selection, selectionArgs)
        val finalMessages = applySortAndLimit(filteredMessages, sortOrder)
        
        AppLog.d(TAG, "Query returning ${finalMessages.size} messages")
        return toSmsCursor(finalMessages, projection)
    }

    override fun getType(uri: Uri): String? {
        return when (uriMatcher.match(uri)) {
            SMS_ALL, SMS_INBOX, SMS_SENT, SMS_DRAFT, SMS_OUTBOX -> 
                "vnd.android.cursor.dir/sms"
            SMS_SINGLE -> 
                "vnd.android.cursor.item/sms"
            else -> null
        }
    }

    override fun insert(uri: Uri, values: ContentValues?): Uri? {
        val context = context ?: return null
        if (values == null) return null
        
        val dao = AppDatabase.getDatabase(context).messageDao()
        
        val message = values.toMessageEntity()
        val id = runBlocking { dao.insert(message) }
        
        val baseUri = Uri.parse("content://$authority/sms")
        return Uri.withAppendedPath(baseUri, id.toString())
    }

    override fun delete(uri: Uri, selection: String?, selectionArgs: Array<out String>?): Int {
        val context = context ?: return 0
        val dao = AppDatabase.getDatabase(context).messageDao()
        
        return runBlocking {
            when (uriMatcher.match(uri)) {
                SMS_SINGLE -> {
                    val id = uri.lastPathSegment?.toLongOrNull() ?: return@runBlocking 0
                    dao.delete(id)
                    1
                }
                else -> 0
            }
        }
    }

    override fun update(
        uri: Uri,
        values: ContentValues?,
        selection: String?,
        selectionArgs: Array<out String>?
    ): Int {
        val context = context ?: return 0
        if (values == null) return 0
        val dao = AppDatabase.getDatabase(context).messageDao()
        
        return runBlocking {
            when (uriMatcher.match(uri)) {
                SMS_SINGLE -> {
                    val id = uri.lastPathSegment?.toLongOrNull() ?: return@runBlocking 0
                    val existing = dao.getById(id) ?: return@runBlocking 0
                    val updated = existing.merge(values)
                    dao.update(updated)
                    1
                }
                else -> 0
            }
        }
    }

    /**
     * Convert MessageEntity list to Android SMS contract Cursor.
     * Supports standard SMS columns as per Android SMS contract.
     */
    private fun toSmsCursor(messages: List<MessageEntity>, projection: Array<out String>?): Cursor {
        // Standard Android SMS columns
        val columns = projection ?: STANDARD_SMS_COLUMNS
        val cursor = MatrixCursor(columns)
        
        messages.forEach { message ->
            val row = arrayOfNulls<Any?>(columns.size)
            columns.forEachIndexed { index, columnName ->
                row[index] = when (columnName) {
                    Telephony.Sms._ID -> message.id
                    Telephony.Sms.THREAD_ID -> message.threadId
                    Telephony.Sms.ADDRESS -> message.sender
                    Telephony.Sms.BODY -> message.body
                    Telephony.Sms.DATE -> message.ts
                    Telephony.Sms.DATE_SENT -> message.dateSent ?: message.ts
                    Telephony.Sms.TYPE -> message.type
                    Telephony.Sms.READ -> if (message.read) 1 else 0
                    Telephony.Sms.SEEN -> if (message.seen) 1 else 0
                    Telephony.Sms.STATUS -> message.status ?: -1
                    Telephony.Sms.SERVICE_CENTER -> message.serviceCenter
                    else -> null
                }
            }
            cursor.addRow(row)
        }
        
        return cursor
    }

    private fun applySelection(
        messages: List<MessageEntity>,
        selection: String?,
        selectionArgs: Array<out String>?
    ): List<MessageEntity> {
        if (selection.isNullOrBlank() || selectionArgs.isNullOrEmpty()) return messages

        val parts = selection.split(Regex("(?i)\\s+AND\\s+"))
        var argIndex = 0
        var filtered = messages

        parts.forEach { rawPart ->
            val part = rawPart.trim().trim('(', ')')
            val match = Regex("(?i)^\\s*([a-zA-Z_]+)\\s*(=|!=|>=|<=|>|<|LIKE)\\s*\\?\\s*$")
                .find(part)
            if (match == null) {
                AppLog.w(TAG, "Unsupported selection clause: $part")
                return@forEach
            }

            if (argIndex >= selectionArgs.size) return@forEach
            val column = match.groupValues[1]
            val op = match.groupValues[2].uppercase()
            val value = selectionArgs[argIndex++]

            filtered = filtered.filter { message ->
                val field = when (column.lowercase()) {
                    Telephony.Sms._ID.lowercase() -> message.id
                    Telephony.Sms.THREAD_ID.lowercase() -> message.threadId
                    Telephony.Sms.ADDRESS.lowercase() -> message.sender
                    Telephony.Sms.BODY.lowercase() -> message.body
                    Telephony.Sms.DATE.lowercase() -> message.ts
                    Telephony.Sms.DATE_SENT.lowercase() -> message.dateSent ?: message.ts
                    Telephony.Sms.TYPE.lowercase() -> message.type
                    Telephony.Sms.READ.lowercase() -> if (message.read) 1 else 0
                    Telephony.Sms.SEEN.lowercase() -> if (message.seen) 1 else 0
                    else -> null
                } ?: return@filter true

                when (op) {
                    "LIKE" -> when (field) {
                        is String -> likeMatch(field, value)
                        else -> false
                    }
                    "=" -> compareEq(field, value)
                    "!=" -> !compareEq(field, value)
                    ">" -> compareNumber(field, value) > 0
                    ">=" -> compareNumber(field, value) >= 0
                    "<" -> compareNumber(field, value) < 0
                    "<=" -> compareNumber(field, value) <= 0
                    else -> true
                }
            }
        }

        return filtered
    }

    private fun applySortAndLimit(messages: List<MessageEntity>, sortOrder: String?): List<MessageEntity> {
        if (sortOrder.isNullOrBlank()) return messages

        val limitMatch = Regex("(?i)\\s+LIMIT\\s+(\\d+)").find(sortOrder)
        val limit = limitMatch?.groupValues?.getOrNull(1)?.toIntOrNull()
        val orderPart = sortOrder.replace(Regex("(?i)\\s+LIMIT\\s+\\d+"), "").trim()

        val orderMatch = Regex("(?i)^\\s*([a-zA-Z_]+)\\s*(ASC|DESC)?\\s*$").find(orderPart)
        val column = orderMatch?.groupValues?.getOrNull(1)
        val direction = orderMatch?.groupValues?.getOrNull(2)?.uppercase() ?: "ASC"

        val sorted = when (column?.lowercase()) {
            Telephony.Sms._ID.lowercase() -> messages.sortedBy { it.id }
            Telephony.Sms.THREAD_ID.lowercase() -> messages.sortedBy { it.threadId }
            Telephony.Sms.ADDRESS.lowercase() -> messages.sortedBy { it.sender }
            Telephony.Sms.DATE.lowercase() -> messages.sortedBy { it.ts }
            Telephony.Sms.DATE_SENT.lowercase() -> messages.sortedBy { it.dateSent ?: it.ts }
            else -> messages
        }.let { list ->
            if (direction == "DESC") list.asReversed() else list
        }

        return if (limit != null) sorted.take(limit) else sorted
    }

    private fun compareEq(field: Any, value: String): Boolean {
        return when (field) {
            is String -> field.equals(value, ignoreCase = true)
            is Int -> field == value.toIntOrNull()
            is Long -> field == value.toLongOrNull()
            else -> false
        }
    }

    private fun compareNumber(field: Any, value: String): Int {
        val target = value.toLongOrNull() ?: return 0
        return when (field) {
            is Int -> field.toLong().compareTo(target)
            is Long -> field.compareTo(target)
            else -> 0
        }
    }

    private fun likeMatch(field: String, pattern: String): Boolean {
        if (!pattern.contains('%') && !pattern.contains('_')) {
            return field.contains(pattern, ignoreCase = true)
        }
        val regexPattern = Regex(
            "^" + Regex.escape(pattern)
                .replace("\\%".toRegex(), ".*")
                .replace("\\_".toRegex(), ".") + "$",
            RegexOption.IGNORE_CASE
        )
        return regexPattern.containsMatchIn(field)
    }

    private fun ContentValues.toMessageEntity(): MessageEntity {
        val address = getAsString(Telephony.Sms.ADDRESS) ?: "UNKNOWN"
        val body = getAsString(Telephony.Sms.BODY) ?: ""
        val date = getAsLong(Telephony.Sms.DATE) ?: System.currentTimeMillis()
        val dateSent = getAsLong(Telephony.Sms.DATE_SENT)
        val type = getAsInteger(Telephony.Sms.TYPE) ?: 1
        val threadId = getAsLong(Telephony.Sms.THREAD_ID) ?: ThreadUtils.calculateThreadId(address)
        val read = getAsInteger(Telephony.Sms.READ)?.let { it != 0 } ?: false
        val seen = getAsInteger(Telephony.Sms.SEEN)?.let { it != 0 } ?: false
        val status = getAsInteger(Telephony.Sms.STATUS)
        val serviceCenter = getAsString(Telephony.Sms.SERVICE_CENTER)
        
        return MessageEntity(
            id = getAsLong(Telephony.Sms._ID) ?: 0L,
            sender = address,
            body = body,
            ts = date,
            threadId = threadId,
            type = type,
            read = read,
            seen = seen,
            status = status,
            serviceCenter = serviceCenter,
            dateSent = dateSent,
            language = null,
            featuresJson = null,
            isOtp = null,
            otpIntent = null,
            isPhishing = null,
            phishScore = null,
            reasonsJson = null,
            reviewed = false,
            version = 1
        )
    }

    private fun MessageEntity.merge(values: ContentValues): MessageEntity {
        return copy(
            sender = values.getAsString(Telephony.Sms.ADDRESS) ?: sender,
            body = values.getAsString(Telephony.Sms.BODY) ?: body,
            ts = values.getAsLong(Telephony.Sms.DATE) ?: ts,
            threadId = values.getAsLong(Telephony.Sms.THREAD_ID) ?: threadId,
            type = values.getAsInteger(Telephony.Sms.TYPE) ?: type,
            read = values.getAsInteger(Telephony.Sms.READ)?.let { it != 0 } ?: read,
            seen = values.getAsInteger(Telephony.Sms.SEEN)?.let { it != 0 } ?: seen,
            status = values.getAsInteger(Telephony.Sms.STATUS) ?: status,
            serviceCenter = values.getAsString(Telephony.Sms.SERVICE_CENTER) ?: serviceCenter,
            dateSent = values.getAsLong(Telephony.Sms.DATE_SENT) ?: dateSent
        )
    }

    companion object {
        private const val TAG = "SmsProvider"
        private const val SMS_ALL = 1
        private const val SMS_SINGLE = 2
        private const val SMS_INBOX = 3
        private const val SMS_SENT = 4
        private const val SMS_DRAFT = 5
        private const val SMS_OUTBOX = 6
        
        // Standard Android SMS columns
        private val STANDARD_SMS_COLUMNS = arrayOf(
            Telephony.Sms._ID,
            Telephony.Sms.THREAD_ID,
            Telephony.Sms.ADDRESS,
            Telephony.Sms.BODY,
            Telephony.Sms.DATE,
            Telephony.Sms.DATE_SENT,
            Telephony.Sms.TYPE,
            Telephony.Sms.READ,
            Telephony.Sms.SEEN,
            Telephony.Sms.STATUS,
            Telephony.Sms.SERVICE_CENTER
        )
    }
}
