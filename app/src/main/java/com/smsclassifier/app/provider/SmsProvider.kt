package com.smsclassifier.app.provider

import android.content.ContentProvider
import android.content.ContentValues
import android.content.UriMatcher
import android.database.Cursor
import android.database.MatrixCursor
import android.net.Uri
import android.util.Log
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.MessageEntity
import kotlinx.coroutines.runBlocking

class SmsProvider : ContentProvider() {

    private val uriMatcher = UriMatcher(UriMatcher.NO_MATCH)
    private var authority: String? = null

    override fun onCreate(): Boolean {
        val ctx = context ?: return false
        authority = "${ctx.packageName}.smsprovider"
        uriMatcher.addURI(authority, "messages", ALL_MESSAGES)
        uriMatcher.addURI(authority, "messages/#", SINGLE_MESSAGE)
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
        val dao = AppDatabase.getDatabase(context).messageDao()
        return when (uriMatcher.match(uri)) {
            ALL_MESSAGES -> {
                val messages = runBlocking { dao.getAllMessages() }
                toCursor(messages)
            }
            SINGLE_MESSAGE -> {
                val id = uri.lastPathSegment?.toLongOrNull() ?: return null
                val message = runBlocking { dao.getById(id) }
                toCursor(message?.let { listOf(it) } ?: emptyList())
            }
            else -> null
        }
    }

    override fun getType(uri: Uri): String? {
        val auth = authority ?: return null
        return when (uriMatcher.match(uri)) {
            ALL_MESSAGES -> "vnd.android.cursor.dir/vnd.$auth.messages"
            SINGLE_MESSAGE -> "vnd.android.cursor.item/vnd.$auth.messages"
            else -> null
        }
    }

    override fun insert(uri: Uri, values: ContentValues?): Uri? {
        val context = context ?: return null
        if (uriMatcher.match(uri) != ALL_MESSAGES) return null
        val dao = AppDatabase.getDatabase(context).messageDao()
        val entity = values.toMessageEntity()
        val id = runBlocking { dao.insert(entity) }
        return Uri.withAppendedPath(uri, id.toString())
    }

    override fun delete(uri: Uri, selection: String?, selectionArgs: Array<out String>?): Int {
        val context = context ?: return 0
        val dao = AppDatabase.getDatabase(context).messageDao()
        return when (uriMatcher.match(uri)) {
            SINGLE_MESSAGE -> {
                val id = uri.lastPathSegment?.toLongOrNull() ?: return 0
                runBlocking { dao.delete(id) }
                1
            }
            else -> 0
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
        return when (uriMatcher.match(uri)) {
            SINGLE_MESSAGE -> {
                val id = uri.lastPathSegment?.toLongOrNull() ?: return 0
                val existing = runBlocking { dao.getById(id) } ?: return 0
                val updated = existing.merge(values)
                runBlocking { dao.update(updated) }
                1
            }
            else -> 0
        }
    }

    private fun toCursor(messages: List<MessageEntity>): Cursor {
        val cursor = MatrixCursor(COLUMNS)
        messages.forEach { message ->
            cursor.addRow(
                arrayOf(
                    message.id,
                    message.sender,
                    message.body,
                    message.ts,
                    message.language,
                    message.featuresJson,
                    message.isOtp?.let { if (it) 1 else 0 },
                    message.otpIntent,
                    message.isPhishing?.let { if (it) 1 else 0 },
                    message.phishScore,
                    message.reasonsJson,
                    if (message.reviewed) 1 else 0
                )
            )
        }
        return cursor
    }

    private fun ContentValues?.toMessageEntity(): MessageEntity {
        val sender = this?.getAsString("sender") ?: "UNKNOWN"
        val body = this?.getAsString("body") ?: ""
        val timestamp = this?.getAsLong("ts") ?: System.currentTimeMillis()
        return MessageEntity(
            id = this?.getAsLong("id") ?: 0L,
            sender = sender,
            body = body,
            ts = timestamp,
            language = this?.getAsString("language"),
            featuresJson = this?.getAsString("featuresJson"),
            isOtp = this?.getAsInteger("isOtp")?.let { it != 0 },
            otpIntent = this?.getAsString("otpIntent"),
            isPhishing = this?.getAsInteger("isPhishing")?.let { it != 0 },
            phishScore = this?.getAsDouble("phishScore")?.toFloat(),
            reasonsJson = this?.getAsString("reasonsJson"),
            reviewed = this?.getAsInteger("reviewed")?.let { it != 0 } ?: false,
            version = 1
        )
    }

    private fun MessageEntity.merge(values: ContentValues): MessageEntity {
        return copy(
            sender = values.getAsString("sender") ?: sender,
            body = values.getAsString("body") ?: body,
            ts = values.getAsLong("ts") ?: ts,
            language = values.getAsString("language") ?: language,
            featuresJson = values.getAsString("featuresJson") ?: featuresJson,
            isOtp = values.getAsInteger("isOtp")?.let { it != 0 } ?: isOtp,
            otpIntent = values.getAsString("otpIntent") ?: otpIntent,
            isPhishing = values.getAsInteger("isPhishing")?.let { it != 0 } ?: isPhishing,
            phishScore = values.getAsDouble("phishScore")?.toFloat() ?: phishScore,
            reasonsJson = values.getAsString("reasonsJson") ?: reasonsJson,
            reviewed = values.getAsInteger("reviewed")?.let { it != 0 } ?: reviewed
        )
    }

    companion object {
        private const val ALL_MESSAGES = 1
        private const val SINGLE_MESSAGE = 2
        private val COLUMNS = arrayOf(
            "id",
            "sender",
            "body",
            "ts",
            "language",
            "featuresJson",
            "isOtp",
            "otpIntent",
            "isPhishing",
            "phishScore",
            "reasonsJson",
            "reviewed"
        )
    }
}
