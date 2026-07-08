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
import com.smsclassifier.app.classification.ServerClassifyException
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

            var serverOfflineSkippedCount = 0
            var serverSuccessCount = 0
            var serverRateLimitedCount = 0
            val serverFailureCounts = mutableMapOf<String, Int>()
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
                            serverOfflineSkippedCount++
                            ClassificationWorkerPolicy.fallbackPrediction(
                                hPred,
                                ClassificationWorkerPolicy.OFFLINE_FALLBACK_REASON
                            )
                        } else {
                            try {
                                val serverPrediction = ServerClassifier(appContext = applicationContext).predict(features)
                                usedServerResult = ClassificationWorkerPolicy.hasUsableServerResult(serverPrediction)
                                if (usedServerResult) {
                                    serverSuccessCount++
                                    serverPrediction
                                } else {
                                    recordServerFailure(serverFailureCounts, "empty_result")
                                    ClassificationWorkerPolicy.fallbackPrediction(
                                        hPred,
                                        ClassificationWorkerPolicy.SERVER_FALLBACK_REASON
                                    )
                                }
                            } catch (e: ServerClassifyException) {
                                AppLog.w(TAG, "Server classify unavailable for ${message.id}: ${e.message}", e)
                                recordServerFailure(serverFailureCounts, e.telemetryReason)
                                if (e.kind == ServerClassifyException.Kind.RATE_LIMITED) {
                                    serverRateLimitedCount++
                                }
                                ClassificationWorkerPolicy.fallbackPrediction(
                                    hPred,
                                    "${e.userMessage} Using basic on-device classification."
                                )
                            } catch (e: Exception) {
                                AppLog.e(TAG, "Server classify failed for ${message.id}: ${e.message}", e)
                                SafeError.report(TAG, e)
                                recordServerFailure(serverFailureCounts, "unknown")
                                ClassificationWorkerPolicy.fallbackPrediction(
                                    hPred,
                                    ClassificationWorkerPolicy.SERVER_FALLBACK_REASON
                                )
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

                    val updatedMessage = ClassificationWorkerPolicy.updatedMessage(
                        message = message,
                        prediction = prediction,
                        usedServerResult = usedServerResult
                    )

                    database.messageDao().update(updatedMessage)
                    AppContainer.telemetry.maybeLogFirstSmsClassified()
                } catch (e: Exception) {
                    AppLog.e(TAG, "Failed to classify message ${message.id}: ${e.message}", e)
                    // Don't retry indefinitely; keep a basic non-OTP fallback so this row leaves the queue.
                    try {
                        val failedMessage = ClassificationWorkerPolicy.failedMessage(
                            message = message,
                            errorMessage = e.message ?: "Unknown error"
                        )
                        database.messageDao().update(failedMessage)
                    } catch (dbError: Exception) {
                        AppLog.e(TAG, "Failed to update message after classification error", dbError)
                    }
                }
            }

            if (serverOfflineSkippedCount > 0) {
                AppContainer.telemetry.logEvent(
                    "server_classify_skipped_offline",
                    mapOf("skipped" to serverOfflineSkippedCount)
                )
            }
            if (serverSuccessCount > 0) {
                AppContainer.telemetry.logEvent(
                    "server_classify_success",
                    mapOf("count" to serverSuccessCount)
                )
            }
            serverFailureCounts.forEach { (reason, count) ->
                AppContainer.telemetry.logEvent(
                    "server_classify_failed",
                    mapOf("reason" to reason, "count" to count)
                )
            }
            if (serverRateLimitedCount > 0) {
                AppContainer.telemetry.logEvent(
                    "server_classify_rate_limited",
                    mapOf("count" to serverRateLimitedCount)
                )
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

        private fun recordServerFailure(counts: MutableMap<String, Int>, reason: String) {
            counts[reason] = (counts[reason] ?: 0) + 1
        }

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
