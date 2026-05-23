package com.smsclassifier.app.work

import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.BuildConfig
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.SettingsRepository
import com.smsclassifier.app.feedback.FeedbackRequest
import com.smsclassifier.app.feedback.FeedbackUploader
import com.smsclassifier.app.util.AppLog
import com.smsclassifier.app.util.SmsRedactor
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class FeedbackUploadWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            val settings = SettingsRepository(applicationContext)
            if (!settings.feedbackUploadEnabled) {
                AppLog.d(TAG, "Skipping feedback upload — toggle disabled")
                return@withContext Result.success()
            }
            val database = AppDatabase.getDatabase(applicationContext)
            val dao = database.misclassificationLogDao()
            val pending = dao.getPendingUpload(PENDING_BATCH)
            if (pending.isEmpty()) {
                AppLog.d(TAG, "No pending misclassification uploads")
                return@withContext Result.success()
            }
            AppLog.d(TAG, "Processing ${pending.size} pending feedback uploads")
            val uploader = FeedbackUploader()
            val installId = settings.installId
            var anyFailure = false
            val now = System.currentTimeMillis()
            val versionCode = BuildConfig.VERSION_CODE
            val versionName = BuildConfig.VERSION_NAME
            var uploadedCount = 0
            var failedCount = 0
            for (row in pending) {
                val bodyLimited = row.body.take(BODY_MAX_LEN)
                val redactedBody = SmsRedactor.redactForTraining(bodyLimited, installId)
                val req = FeedbackRequest(
                    installId = installId,
                    firebaseUid = null,
                    appVersionCode = versionCode,
                    appVersionName = versionName,
                    sender = row.sender,
                    body = redactedBody,
                    bodyRedactionScheme = "digits_v1",
                    predictedIsOtp = row.predictedIsOtp,
                    predictedOtpIntent = row.predictedOtpIntent,
                    predictedIsPhishing = row.predictedIsPhishing,
                    predictedPhishScore = row.predictedPhishScore,
                    userCorrection = row.userNote,
                    userNote = null,
                    clientCreatedAt = row.createdAt,
                    feedbackKind = row.feedbackKind
                )
                val result = uploader.upload(req)
                if (result.isSuccess) {
                    dao.markUploaded(row.id, now)
                    uploadedCount++
                } else {
                    dao.markUploadAttempt(row.id, now)
                    failedCount++
                    anyFailure = true
                }
            }
            AppContainer.telemetry.logEvent(
                "feedback_upload_result",
                mapOf(
                    "success" to (!anyFailure).toString(),
                    "uploaded" to uploadedCount,
                    "failed" to failedCount
                )
            )
            if (anyFailure) Result.retry() else Result.success()
        } catch (e: Exception) {
            AppLog.e(TAG, "Feedback upload worker failed", e)
            Result.retry()
        }
    }

    companion object {
        private const val TAG = "FeedbackUploadWorker"
        private const val WORK_NAME = "feedback_upload"
        private const val PENDING_BATCH = 50
        private const val BODY_MAX_LEN = 4000

        fun enqueue(context: Context) {
            AppLog.d(TAG, "Enqueue feedback upload job")
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
            val request = OneTimeWorkRequestBuilder<FeedbackUploadWorker>()
                .setConstraints(constraints)
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
                .build()
            WorkManager.getInstance(context.applicationContext).enqueueUniqueWork(
                WORK_NAME,
                ExistingWorkPolicy.KEEP,
                request
            )
        }
    }
}
