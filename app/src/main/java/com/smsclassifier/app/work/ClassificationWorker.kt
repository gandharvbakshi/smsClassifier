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
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.classification.FeatureExtractor
import com.smsclassifier.app.classification.HeuristicOnlyClassifier
import com.smsclassifier.app.classification.ServerClassifier
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.util.PerformanceTracker
import com.smsclassifier.app.util.SafeError
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class ClassificationWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    private fun hasInternet(): Boolean {
        val cm = applicationContext.getSystemService(Context.CONNECTIVITY_SERVICE)
            as? android.net.ConnectivityManager ?: return false
        val network = cm.activeNetwork ?: return false
        val caps = cm.getNetworkCapabilities(network) ?: return false
        return caps.hasCapability(android.net.NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        AppLog.d(TAG, "doWork() started")
        try {
            val database = AppDatabase.getDatabase(applicationContext)
            AppLog.d(TAG, "Database initialized")

            val featureExtractor = FeatureExtractor(applicationContext)
            val unclassifiedMessages = database.messageDao().getUnclassified(limit = BATCH_LIMIT)
            AppLog.d(TAG, "Found ${unclassifiedMessages.size} unclassified messages")

            if (unclassifiedMessages.isEmpty()) {
                AppLog.d(TAG, "No unclassified messages")
                return@withContext Result.success()
            }

            AppLog.d(TAG, "Classifying ${unclassifiedMessages.size} messages")

            unclassifiedMessages.forEach { message ->
                try {
                    if (message.body.isBlank()) {
                        AppLog.w(TAG, "Skipping empty message ${message.id}")
                        val emptyMessage = message.copy(
                            isOtp = false,
                            otpIntent = null,
                            isPhishing = null,
                            phishScore = null,
                            reasonsJson = null,
                            reviewed = true
                        )
                        database.messageDao().update(emptyMessage)
                        return@forEach
                    }

                    val features = featureExtractor.extractFeatures(message.body, message.sender)
                    val heuristicClassifier = HeuristicOnlyClassifier()
                    val hPred = heuristicClassifier.predict(features)

                    val useServer = AppContainer.entitlementManager
                        .shouldUseServerForMessage(hPred.isOtp == true)

                    var usedServerResult = false
                    val prediction = if (useServer) {
                        if (!hasInternet()) {
                            AppLog.d(TAG, "Skipping server classify (offline); using heuristic for message ${message.id}")
                            AppContainer.telemetry.logEvent("server_classify_skipped_offline", emptyMap())
                            hPred
                        } else {
                        try {
                            ServerClassifier().predict(features).also { serverPrediction ->
                                usedServerResult = serverPrediction.isOtp != null ||
                                    serverPrediction.isPhishing != null
                            }
                        } catch (e: Exception) {
                            AppLog.e(TAG, "Server classify failed for ${message.id}: ${e.message}", e)
                            SafeError.report(TAG, e)
                            hPred
                        }
                        }
                    } else {
                        hPred
                    }

                    // Track performance metrics
                    if (prediction.inferenceTimeMs > 0) {
                        PerformanceTracker.recordLatency(applicationContext, prediction.inferenceTimeMs)
                    }

                    AppLog.d(
                        TAG,
                        "Message ${message.id} otp=${prediction.isOtp} phishing=${prediction.isPhishing} intent=${prediction.otpIntent} server=$useServer"
                    )

                    if (prediction.isOtp == true) {
                        AppContainer.entitlementManager.onWorkerDetectedOtp()
                    }

                    val updatedMessage = message.copy(
                        isOtp = prediction.isOtp,
                        otpIntent = if (usedServerResult) prediction.otpIntent else null,
                        isPhishing = if (usedServerResult) prediction.isPhishing else null,
                        phishScore = if (usedServerResult) prediction.phishScore else null,
                        reasonsJson = if (useServer && prediction.reasons.isNotEmpty()) {
                            prediction.reasons.joinToString(",") { "\"$it\"" }.let { "[$it]" }
                        } else {
                            null
                        },
                        reviewed = if (useServer) message.reviewed else true
                    )

                    database.messageDao().update(updatedMessage)
                    AppContainer.telemetry.maybeLogFirstSmsClassified()
                } catch (e: Exception) {
                    AppLog.e(TAG, "Failed to classify message ${message.id}: ${e.message}", e)
                    // Don't retry indefinitely - mark as needing review after failures
                    try {
                        val failedMessage = message.copy(
                            reasonsJson = "[\"Classification error: ${e.message?.take(50) ?: "Unknown error"}\"]"
                        )
                        database.messageDao().update(failedMessage)
                    } catch (dbError: Exception) {
                        AppLog.e(TAG, "Failed to update message after classification error", dbError)
                    }
                }
            }

            val hasMore = database.messageDao().getUnclassified(limit = 1).isNotEmpty()
            if (hasMore) {
                AppLog.d(TAG, "More unclassified messages remain; queueing next classification batch")
                enqueue(applicationContext)
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
        private const val BATCH_LIMIT = 50

        fun enqueue(context: Context) {
            AppLog.d(TAG, "Enqueuing classification work")

            // Heuristic-first design: workers must run offline for FREE-tier users.
            // Server call inside doWork is best-effort and short-circuits when offline.
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.NOT_REQUIRED)
                .build()

            val request = OneTimeWorkRequestBuilder<ClassificationWorker>()
                .setConstraints(constraints)
                .addTag("classification")
                .build()

            WorkManager.getInstance(context).enqueueUniqueWork(
                WORK_NAME,
                ExistingWorkPolicy.APPEND_OR_REPLACE,
                request
            )
            AppLog.d(TAG, "Work enqueued successfully with id=${request.id}")
        }
    }
}
