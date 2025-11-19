package com.smsclassifier.app.classification

import android.util.Log
import com.smsclassifier.app.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit

@Serializable
data class ServerRequest(
    val text: String,
    val sender: String? = null,
    val features: Map<String, Float>? = null
)

@Serializable
data class ServerResponse(
    val isOtp: Boolean? = null,
    val otpIntent: String? = null,
    val isPhishing: Boolean? = null,
    val phishScore: Float = 0f,
    val reasons: List<String> = emptyList()
)

class ServerClassifier(
    private val baseUrl: String = BuildConfig.SERVER_API_BASE_URL,
    private val timeoutSeconds: Int = 10  // Increased timeout for Cloud Run
) : Classifier {
    
    companion object {
        private const val TAG = "ServerClassifier"
    }
    private val client = OkHttpClient.Builder()
        .connectTimeout(timeoutSeconds.toLong(), TimeUnit.SECONDS)
        .readTimeout(timeoutSeconds.toLong(), TimeUnit.SECONDS)
        .writeTimeout(timeoutSeconds.toLong(), TimeUnit.SECONDS)
        .build()

    private var retryCount = 0
    private val maxRetries = 3

    override suspend fun predict(input: MessageFeatures): Prediction = withContext(Dispatchers.IO) {
        val startTime = System.currentTimeMillis()
        val url = "$baseUrl/classify"
        Log.d(TAG, "Making request to $url")
        Log.d(TAG, "Request text length: ${input.text.length}, sender: ${input.sender}")
        
        val requestBody = Json.encodeToString(
            ServerRequest(
                text = input.text,
                sender = input.sender,
                features = input.heuristicFeatures?.let { features ->
                    features.mapIndexed { index, value -> "feature_$index" to value }.toMap()
                }
            )
        ).toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url(url)
            .post(requestBody)
            .build()

        var lastException: Exception? = null
        
        repeat(maxRetries) { attempt ->
            try {
                val response = client.newCall(request).execute()
                val responseBody = response.body?.string() ?: throw IOException("Empty response")
                
                if (response.isSuccessful) {
                    val serverResponse = Json.decodeFromString<ServerResponse>(responseBody)
                    val inferenceTime = System.currentTimeMillis() - startTime
                    
                    return@withContext Prediction(
                        isOtp = serverResponse.isOtp,
                        otpIntent = serverResponse.otpIntent,
                        isPhishing = serverResponse.isPhishing,
                        phishScore = serverResponse.phishScore,
                        reasons = serverResponse.reasons,
                        inferenceTimeMs = inferenceTime
                    )
                } else {
                    throw IOException("Server error: ${response.code}")
                }
            } catch (e: Exception) {
                lastException = e
                Log.w(TAG, "Attempt ${attempt + 1} failed: ${e.message}", e)
                
                // Exponential backoff
                if (attempt < maxRetries - 1) {
                    val delayMs = (1000 * (1 shl attempt)).toLong()
                    Thread.sleep(delayMs)
                }
            }
        }
        
        // All retries failed
        Log.e(TAG, "All retry attempts failed: ${lastException?.message}", lastException)
        val inferenceTime = System.currentTimeMillis() - startTime
        
        Prediction(
            isOtp = null,
            otpIntent = null,
            isPhishing = null,
            phishScore = 0f,
            reasons = listOf("Server error: ${lastException?.message}"),
            inferenceTimeMs = inferenceTime
        )
    }

    override fun isAvailable(): Boolean {
        return true // Always available (will fail gracefully)
    }
}

