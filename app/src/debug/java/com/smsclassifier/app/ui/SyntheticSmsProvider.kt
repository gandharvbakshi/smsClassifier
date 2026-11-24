package com.smsclassifier.app.ui

import android.content.ContentProvider
import android.content.ContentValues
import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import android.net.Uri
import com.smsclassifier.app.data.MessageEntity

/**
 * In-memory SMS provider used by debug instrumentation. It never reads or writes
 * the device Telephony provider.
 */
class SyntheticSmsProvider : ContentProvider() {
    override fun onCreate(): Boolean {
        ensureStore()
        return true
    }

    override fun query(
        uri: Uri,
        projection: Array<out String>?,
        selection: String?,
        selectionArgs: Array<out String>?,
        sortOrder: String?
    ): Cursor {
        ensureStore()
        return store.query("sms", projection, selection, selectionArgs, null, null, sortOrder)
    }

    override fun getType(uri: Uri): String? = null

    override fun insert(uri: Uri, values: ContentValues?): Uri? = null

    override fun delete(uri: Uri, selection: String?, selectionArgs: Array<out String>?): Int {
        ensureStore()
        return store.delete("sms", selection, selectionArgs)
    }

    override fun update(
        uri: Uri,
        values: ContentValues?,
        selection: String?,
        selectionArgs: Array<out String>?
    ): Int = 0

    companion object {
        private const val CREATE_SQL = """
            CREATE TABLE sms (
                _id INTEGER PRIMARY KEY,
                address TEXT,
                body TEXT,
                date INTEGER,
                type INTEGER
            )
        """
        private var database: SQLiteDatabase? = null
        private val store: SQLiteDatabase
            get() = requireNotNull(database)

        fun reset() {
            synchronized(this) {
                database?.takeIf { it.isOpen }?.close()
                database = SQLiteDatabase.create(null).also { it.execSQL(CREATE_SQL.trimIndent()) }
            }
        }

        fun add(id: Long, message: MessageEntity) {
            ensureStore()
            store.insert("sms", null, ContentValues().apply {
                put("_id", id)
                put("address", message.sender)
                put("body", message.body)
                put("date", message.ts)
                put("type", message.type)
            })
        }

        fun ids(): Set<Long> {
            ensureStore()
            return store.query("sms", arrayOf("_id"), null, null, null, null, null).use { cursor ->
                buildSet {
                    while (cursor.moveToNext()) add(cursor.getLong(0))
                }
            }
        }

        private fun ensureStore() {
            synchronized(this) {
                if (database?.isOpen != true) {
                    database = SQLiteDatabase.create(null).also { it.execSQL(CREATE_SQL.trimIndent()) }
                }
            }
        }
    }
}
