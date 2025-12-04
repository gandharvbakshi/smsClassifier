package com.smsclassifier.app.work

import android.content.Context
import androidx.work.Constraints
import com.smsclassifier.app.util.AppLog
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.smsclassifier.app.classification.Classifier
import com.smsclassifier.app.classification.FeatureExtractor
import com.smsclassifier.app.classification.ServerClassifier
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.MessageEntity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class ClassificationWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        AppLog.d(TAG, "doWork() started")
        try {
            val database = AppDatabase.getDatabase(applicationContext)
            AppLog.d(TAG, "Database initialized")
            
            val classifier: Classifier = ServerClassifier()
            AppLog.d(TAG, "ServerClassifier initialized")

            val featureExtractor = FeatureExtractor(applicationContext)
            val unclassifiedMessages = database.messageDao().getUnclassified(limit = 10)
            AppLog.d(TAG, "Found ${unclassifiedMessages.size} unclassified messages")

            if (unclassifiedMessages.isEmpty()) {
                AppLog.d(TAG, "No unclassified messages")
                return@withContext Result.success()
            }

            AppLog.d(TAG, "Classifying ${unclassifiedMessages.size} messages")

            unclassifiedMessages.forEach { message ->
                try {
                    val features = featureExtractor.extractFeatures(message.body, message.sender)
                    val prediction = classifier.predict(features)
                    AppLog.d(
                        TAG,
                        "Message ${message.id} otp=${prediction.isOtp} phishing=${prediction.isPhishing} intent=${prediction.otpIntent}"
                    )

                    val updatedMessage = message.copy(
                        isOtp = prediction.isOtp,
                        otpIntent = prediction.otpIntent,
                        isPhishing = prediction.isPhishing,
                        phishScore = prediction.phishScore,
                        reasonsJson = prediction.reasons.joinToString(",") { "\"$it\"" }.let { "[$it]" }
                    )

                    database.messageDao().update(updatedMessage)
                } catch (e: Exception) {
                    AppLog.e(TAG, "Failed to classify message ${message.id}", e)
                }
            }

            AppLog.d(TAG, "Classification completed successfully")
            Result.success()
        } catch (e: Exception) {
            AppLog.e(TAG, "Classification failed", e)
            Result.retry()
        }
    }

    companion object {
        private const val TAG = "ClassificationWorker"
        private const val WORK_NAME = "classify_sms"

        fun enqueue(context: Context) {
            AppLog.d(TAG, "Enqueuing classification work")
            
            // Temporarily use NOT_REQUIRED to test if network constraint is blocking
            // Will change back to CONNECTED once we confirm worker runs
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.NOT_REQUIRED)  // Changed for testing
                .build()

            val request = OneTimeWorkRequestBuilder<ClassificationWorker>()
                .setConstraints(constraints)
                .addTag("classification")
                .build()

            WorkManager.getInstance(context).enqueueUniqueWork(
                WORK_NAME,
                ExistingWorkPolicy.REPLACE,
                request
            )
            AppLog.d(TAG, "Work enqueued successfully with id=${request.id}")
        }
    }
}

