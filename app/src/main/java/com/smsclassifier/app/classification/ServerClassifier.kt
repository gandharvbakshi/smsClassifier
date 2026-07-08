package com.smsclassifier.app.classification

import android.content.Context
import com.google.firebase.auth.FirebaseAuth
import com.smsclassifier.app.BuildConfig
import com.smsclassifier.app.data.SettingsRepository
import com.smsclassifier.app.util.AppLog
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
    val features: Map<String, Float>? = null,
    val installId: String? = null,
    val firebaseUid: String? = null,
    val appVersionCode: Int? = null,
    val appVersionName: String? = null
)

@Serializable
data class ServerResponse(
    val isOtp: Boolean? = null,
    val otpIntent: String? = null,
    val isPhishing: Boolean? = null,
    val phishScore: Float = 0f,
    val reasons: List<String> = emptyList()
)

class ServerClassifyException(
    val kind: Kind,
    val statusCode: Int? = null,
    message: String,
    cause: Throwable? = null
) : IOException(message, cause) {
    enum class Kind {
        RATE_LIMITED,
        TIMEOUT,
        NETWORK,
        SERVER,
        CLIENT,
        UNKNOWN
    }

    val retryable: Boolean
        get() = kind == Kind.TIMEOUT || kind == Kind.NETWORK || kind == Kind.SERVER || kind == Kind.UNKNOWN

    val telemetryReason: String
        get() = when (kind) {
            Kind.RATE_LIMITED -> "rate_limited"
            Kind.TIMEOUT -> "timeout"
            Kind.NETWORK -> "network"
            Kind.SERVER -> "server"
            Kind.CLIENT -> "client"
            Kind.UNKNOWN -> "unknown"
        }

    val userMessage: String
        get() = when (kind) {
            Kind.RATE_LIMITED -> "Cloud check is busy right now."
            Kind.TIMEOUT -> "Cloud check timed out."
            Kind.NETWORK -> "Cloud check could not connect."
            Kind.SERVER -> "Cloud check is temporarily unavailable."
            Kind.CLIENT -> "Cloud check request was rejected."
            Kind.UNKNOWN -> "Cloud check failed."
        }

    companion object {
        fun fromStatus(code: Int): ServerClassifyException {
            val kind = when (code) {
                429 -> Kind.RATE_LIMITED
                in 500..599 -> Kind.SERVER
                in 400..499 -> Kind.CLIENT
                else -> Kind.UNKNOWN
            }
            return ServerClassifyException(
                kind = kind,
                statusCode = code,
                message = "Server error: $code"
            )
        }

        fun fromException(error: Exception): ServerClassifyException {
            if (error is ServerClassifyException) return error
            val kind = when (error) {
                is java.net.SocketTimeoutException -> Kind.TIMEOUT
                is java.net.UnknownHostException,
                is java.net.ConnectException -> Kind.NETWORK
                else -> when {
                    error.cause is java.net.SocketTimeoutException -> Kind.TIMEOUT
                    error.cause is java.net.UnknownHostException ||
                        error.cause is java.net.ConnectException -> Kind.NETWORK
                    else -> Kind.UNKNOWN
                }
            }
            return ServerClassifyException(
                kind = kind,
                message = error.message ?: "Server classify failed",
                cause = error
            )
        }
    }
}

class ServerClassifier(
    private val baseUrl: String = BuildConfig.SERVER_API_BASE_URL,
    private val timeoutSeconds: Int = 10,  // Increased timeout for Cloud Run
    private val appContext: Context? = null
) : Classifier {
    
    companion object {
        private const val TAG = "ServerClassifier"
    }
    private val client = OkHttpClient.Builder()
        .connectTimeout(timeoutSeconds.toLong(), TimeUnit.SECONDS)
        .readTimeout(timeoutSeconds.toLong(), TimeUnit.SECONDS)
        .writeTimeout(timeoutSeconds.toLong(), TimeUnit.SECONDS)
        .build()

    private val maxRetries = 3

    override suspend fun predict(input: MessageFeatures): Prediction = withContext(Dispatchers.IO) {
        val startTime = System.currentTimeMillis()
        val url = "$baseUrl/classify"
        AppLog.d(TAG, "Making request to $url")
        AppLog.d(TAG, "Request text length: ${input.text.length}")
        val installId = appContext?.let { SettingsRepository(it).installId }
        
        val requestBody = Json.encodeToString(
            ServerRequest(
                text = input.text,
                sender = input.sender,
                features = input.heuristicFeatures?.let { features ->
                    features.mapIndexed { index, value -> "feature_$index" to value }.toMap()
                },
                installId = installId,
                firebaseUid = FirebaseAuth.getInstance().currentUser?.uid,
                appVersionCode = BuildConfig.VERSION_CODE,
                appVersionName = BuildConfig.VERSION_NAME
            )
        ).toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url(url)
            .post(requestBody)
            .build()

        var lastException: Exception? = null
        
        repeat(maxRetries) { attempt ->
            try {
                client.newCall(request).execute().use { response ->
                    val responseBody = response.body?.string() ?: throw IOException("Empty response")

                    if (!response.isSuccessful) {
                        throw ServerClassifyException.fromStatus(response.code)
                    }

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
                }
            } catch (e: Exception) {
                val failure = ServerClassifyException.fromException(e)
                lastException = failure
                AppLog.w(TAG, "Attempt ${attempt + 1} failed: ${failure.message}", failure)

                if (!failure.retryable || attempt == maxRetries - 1) {
                    AppLog.e(TAG, "Server classify failed", failure)
                    throw failure
                }

                // Exponential backoff
                val delayMs = (1000 * (1 shl attempt)).toLong()
                Thread.sleep(delayMs)
            }
        }
        
        throw ServerClassifyException.fromException(
            lastException ?: IOException("Server classify failed")
        )
    }

    override fun isAvailable(): Boolean {
        return true // Always available (will fail gracefully)
    }
}

