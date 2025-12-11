package com.smsclassifier.app.util

import com.smsclassifier.app.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.*
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * Utility class to check backend API health status.
 */
object BackendHealthChecker {
    private const val TAG = "BackendHealthChecker"
    private val client = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(5, TimeUnit.SECONDS)
        .build()

    data class HealthStatus(
        val isHealthy: Boolean,
        val responseTimeMs: Long? = null,
        val errorMessage: String? = null,
        val lastChecked: Long = System.currentTimeMillis()
    )

    /**
     * Check backend health by making a simple request to the classify endpoint.
     * Returns health status with response time and any errors.
     */
    suspend fun checkHealth(): HealthStatus = withContext(Dispatchers.IO) {
        val startTime = System.currentTimeMillis()
        val healthCheckUrl = "${BuildConfig.SERVER_API_BASE_URL}/health"
        val fallbackUrl = "${BuildConfig.SERVER_API_BASE_URL}/classify"
        
        try {
            // Try health endpoint first, fallback to classify endpoint
            val urlsToTry = listOf(healthCheckUrl, fallbackUrl)
            
            for (url in urlsToTry) {
                try {
                    val request = Request.Builder()
                        .url(url)
                        .head() // Use HEAD request for health check to avoid processing
                        .build()
                    
                    val response = client.newCall(request).execute()
                    val responseTime = System.currentTimeMillis() - startTime
                    
                    if (response.isSuccessful || response.code == 405) { // 405 = Method Not Allowed is OK for health check
                        AppLog.d(TAG, "Backend health check successful: $url (${responseTime}ms)")
                        return@withContext HealthStatus(
                            isHealthy = true,
                            responseTimeMs = responseTime
                        )
                    }
                } catch (e: Exception) {
                    AppLog.w(TAG, "Health check failed for $url: ${e.message}")
                    if (url == urlsToTry.last()) {
                        throw e
                    }
                }
            }
            
            // If we get here, all URLs failed
            val responseTime = System.currentTimeMillis() - startTime
            HealthStatus(
                isHealthy = false,
                responseTimeMs = responseTime,
                errorMessage = "Unable to reach backend service"
            )
        } catch (e: Exception) {
            val responseTime = System.currentTimeMillis() - startTime
            val errorMessage = when {
                e is IOException && e.message?.contains("Unable to resolve host") == true -> 
                    "Backend service is unreachable. Check your internet connection."
                e is java.net.SocketTimeoutException -> 
                    "Backend service is not responding. It may be temporarily unavailable."
                e is java.net.ConnectException -> 
                    "Unable to connect to backend service."
                else -> 
                    "Backend health check failed: ${e.message}"
            }
            
            AppLog.e(TAG, "Backend health check failed", e)
            HealthStatus(
                isHealthy = false,
                responseTimeMs = responseTime,
                errorMessage = errorMessage
            )
        }
    }
}

