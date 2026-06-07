package com.smsclassifier.app.work

import android.Manifest
import android.app.role.RoleManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.provider.Telephony
import androidx.core.content.ContextCompat
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.util.AppLog
import com.smsclassifier.app.util.ThreadUtils
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class SmsImportWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        if (!canImport(applicationContext)) {
            AppLog.w(TAG, "Skipping SMS import: default role or READ_SMS is missing")
            return@withContext Result.success()
        }

        val prefs = applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val imported = runCatching { importBatch(prefs) }.getOrElse { throwable ->
            AppLog.e(TAG, "SMS import failed", throwable)
            AppContainer.telemetry.logEvent(
                "sms_import_failed",
                mapOf("error" to throwable.javaClass.simpleName)
            )
            return@withContext Result.retry()
        }

        if (imported.inserted > 0) {
            ClassificationWorker.enqueue(applicationContext)
        }

        AppContainer.telemetry.logEvent(
            "sms_import_batch",
            mapOf(
                "inserted" to imported.inserted,
                "scanned" to imported.scanned,
                "has_more" to imported.hasMore.toString()
            )
        )

        if (imported.hasMore) {
            enqueue(applicationContext)
        }
        Result.success()
    }

    private suspend fun importBatch(prefs: android.content.SharedPreferences): ImportResult {
        val database = AppDatabase.getDatabase(applicationContext)
        val dao = database.messageDao()
        val lastImportedId = prefs.getLong(KEY_LAST_IMPORTED_ID, 0L)
        var highestSeenId = lastImportedId
        var scanned = 0
        var inserted = 0
        var hasMore = false

        val projection = arrayOf(
            Telephony.Sms._ID,
            Telephony.Sms.ADDRESS,
            Telephony.Sms.BODY,
            Telephony.Sms.DATE,
            Telephony.Sms.THREAD_ID,
            Telephony.Sms.TYPE,
            Telephony.Sms.READ,
            Telephony.Sms.SEEN,
            Telephony.Sms.STATUS,
            Telephony.Sms.SERVICE_CENTER,
            Telephony.Sms.DATE_SENT
        )

        val sortOrder = "${Telephony.Sms._ID} ASC LIMIT $BATCH_LIMIT"
        applicationContext.contentResolver.query(
            Telephony.Sms.CONTENT_URI,
            projection,
            "${Telephony.Sms._ID} > ?",
            arrayOf(lastImportedId.toString()),
            sortOrder
        )?.use { cursor ->
            hasMore = cursor.count >= BATCH_LIMIT
            val idIdx = cursor.getColumnIndex(Telephony.Sms._ID)
            val addressIdx = cursor.getColumnIndex(Telephony.Sms.ADDRESS)
            val bodyIdx = cursor.getColumnIndex(Telephony.Sms.BODY)
            val dateIdx = cursor.getColumnIndex(Telephony.Sms.DATE)
            val threadIdx = cursor.getColumnIndex(Telephony.Sms.THREAD_ID)
            val typeIdx = cursor.getColumnIndex(Telephony.Sms.TYPE)
            val readIdx = cursor.getColumnIndex(Telephony.Sms.READ)
            val seenIdx = cursor.getColumnIndex(Telephony.Sms.SEEN)
            val statusIdx = cursor.getColumnIndex(Telephony.Sms.STATUS)
            val serviceCenterIdx = cursor.getColumnIndex(Telephony.Sms.SERVICE_CENTER)
            val dateSentIdx = cursor.getColumnIndex(Telephony.Sms.DATE_SENT)

            while (cursor.moveToNext()) {
                scanned++
                val providerId = cursor.getLongOrNull(idIdx) ?: continue
                highestSeenId = maxOf(highestSeenId, providerId)
                val body = cursor.getStringOrBlank(bodyIdx)
                val sender = cursor.getStringOrBlank(addressIdx).ifBlank { "UNKNOWN" }
                val ts = cursor.getLongOrNull(dateIdx) ?: continue
                val type = cursor.getIntOrDefault(typeIdx, Telephony.Sms.MESSAGE_TYPE_INBOX)

                if (body.isBlank()) continue
                if (dao.countBySourceProviderId(providerId) > 0) continue
                if (dao.countEquivalent(sender, body, ts, type) > 0) continue

                val providerThreadId = cursor.getLongOrNull(threadIdx)
                val threadId = providerThreadId?.takeIf { it > 0L }
                    ?: ThreadUtils.calculateThreadId(sender)

                dao.insert(
                    MessageEntity(
                        sender = sender,
                        body = body,
                        ts = ts,
                        threadId = threadId,
                        type = type,
                        read = cursor.getBooleanFromInt(readIdx),
                        seen = cursor.getBooleanFromInt(seenIdx),
                        status = cursor.getIntOrNull(statusIdx),
                        serviceCenter = cursor.getStringOrNull(serviceCenterIdx),
                        dateSent = cursor.getLongOrNull(dateSentIdx),
                        sourceProviderId = providerId
                    )
                )
                inserted++
            }
        }

        if (highestSeenId > lastImportedId) {
            prefs.edit()
                .putLong(KEY_LAST_IMPORTED_ID, highestSeenId)
                .putLong(KEY_LAST_IMPORT_AT_MS, System.currentTimeMillis())
                .apply()
        }

        AppLog.d(
            TAG,
            "Imported SMS batch scanned=$scanned inserted=$inserted lastId=$highestSeenId hasMore=$hasMore"
        )
        return ImportResult(scanned = scanned, inserted = inserted, hasMore = hasMore)
    }

    private data class ImportResult(
        val scanned: Int,
        val inserted: Int,
        val hasMore: Boolean
    )

    companion object {
        private const val TAG = "SmsImportWorker"
        private const val WORK_NAME = "import_existing_sms"
        private const val PREFS_NAME = "sms_import_prefs"
        private const val KEY_LAST_IMPORTED_ID = "last_imported_provider_id"
        private const val KEY_LAST_IMPORT_AT_MS = "last_import_at_ms"
        private const val BATCH_LIMIT = 300

        fun enqueue(context: Context) {
            val appContext = context.applicationContext
            if (!canImport(appContext)) {
                AppLog.w(TAG, "Not enqueuing SMS import until default role and READ_SMS are granted")
                return
            }

            val request = OneTimeWorkRequestBuilder<SmsImportWorker>()
                .addTag("sms_import")
                .build()

            WorkManager.getInstance(appContext).enqueueUniqueWork(
                WORK_NAME,
                ExistingWorkPolicy.APPEND_OR_REPLACE,
                request
            )
        }

        fun canImport(context: Context): Boolean {
            val isDefault = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val roleManager = context.getSystemService(RoleManager::class.java)
                roleManager?.isRoleHeld(RoleManager.ROLE_SMS) ?: false
            } else {
                Telephony.Sms.getDefaultSmsPackage(context) == context.packageName
            }
            val hasReadSms = ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.READ_SMS
            ) == PackageManager.PERMISSION_GRANTED
            return isDefault && hasReadSms
        }
    }
}

private fun android.database.Cursor.getStringOrNull(index: Int): String? =
    if (index >= 0 && !isNull(index)) getString(index) else null

private fun android.database.Cursor.getStringOrBlank(index: Int): String =
    getStringOrNull(index)?.trim().orEmpty()

private fun android.database.Cursor.getLongOrNull(index: Int): Long? =
    if (index >= 0 && !isNull(index)) getLong(index) else null

private fun android.database.Cursor.getIntOrNull(index: Int): Int? =
    if (index >= 0 && !isNull(index)) getInt(index) else null

private fun android.database.Cursor.getIntOrDefault(index: Int, defaultValue: Int): Int =
    getIntOrNull(index) ?: defaultValue

private fun android.database.Cursor.getBooleanFromInt(index: Int): Boolean =
    getIntOrDefault(index, 0) != 0
