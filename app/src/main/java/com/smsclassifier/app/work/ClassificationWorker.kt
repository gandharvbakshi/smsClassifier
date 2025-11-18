package com.smsclassifier.app.work

import android.content.Context
import android.util.Log
import androidx.work.Constraints
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
        try {
            val database = AppDatabase.getDatabase(applicationContext)
            val classifier: Classifier = ServerClassifier()

            val featureExtractor = FeatureExtractor(applicationContext)
            val unclassifiedMessages = database.messageDao().getUnclassified(limit = 10)

            if (unclassifiedMessages.isEmpty()) {
                Log.d("ClassificationWorker", "No unclassified messages")
                return@withContext Result.success()
            }

            Log.d("ClassificationWorker", "Classifying ${unclassifiedMessages.size} messages")

            unclassifiedMessages.forEach { message ->
                try {
                    val features = featureExtractor.extractFeatures(message.body, message.sender)
                    val prediction = classifier.predict(features)
                    Log.d(
                        "ClassificationWorker",
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
                    Log.e("ClassificationWorker", "Failed to classify message ${message.id}", e)
                }
            }

            Result.success()
        } catch (e: Exception) {
            Log.e("ClassificationWorker", "Classification failed", e)
            Result.retry()
        }
    }

    companion object {
        private const val WORK_NAME = "classify_sms"

        fun enqueue(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .setRequiresBatteryNotLow(true)
                .build()

            val request = OneTimeWorkRequestBuilder<ClassificationWorker>()
                .setConstraints(constraints)
                .build()

            WorkManager.getInstance(context).enqueueUniqueWork(
                WORK_NAME,
                ExistingWorkPolicy.REPLACE,
                request
            )
        }
    }
}

