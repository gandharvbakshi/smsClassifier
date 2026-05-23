package com.smsclassifier.app.feedback

import com.smsclassifier.app.BuildConfig
import com.smsclassifier.app.util.AppLog
import com.smsclassifier.app.util.SmsRedactor
import java.io.IOException
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody

private val feedbackJson = Json {
    ignoreUnknownKeys = true
    isLenient = true
}

@Serializable
data class FeedbackRequest(
    val installId: String,
    val firebaseUid: String? = null,
    val appVersionCode: Int,
    val appVersionName: String,
    val sender: String,
    val body: String,
    val bodyRedactionScheme: String = SmsRedactor.TRAINING_REDACTION_SCHEME,
    val predictedIsOtp: Boolean? = null,
    val predictedOtpIntent: String? = null,
    val predictedIsPhishing: Boolean? = null,
    val predictedPhishScore: Float? = null,
    val userCorrection: String?,
    val userNote: String? = null,
    val clientCreatedAt: Long,
    val feedbackKind: String? = null,
    val satisfactionScore: Int? = null
)

@Serializable
data class FeedbackResponse(
    val ok: Boolean = false,
    val id: String? = null,
    val error: String? = null
)

class FeedbackUploader(
    private val baseUrl: String = BuildConfig.SERVER_API_BASE_URL
) {

    companion object {
        private const val TAG = "FeedbackUploader"
    }

    private val client = OkHttpClient.Builder()
        .connectTimeout(10L, TimeUnit.SECONDS)
        .readTimeout(10L, TimeUnit.SECONDS)
        .writeTimeout(10L, TimeUnit.SECONDS)
        .build()

    suspend fun upload(req: FeedbackRequest): Result<String> = withContext(Dispatchers.IO) {
        try {
            val url = "${baseUrl.trimEnd('/')}/feedback"
            val jsonBody = feedbackJson.encodeToString(req).toByteArray(Charsets.UTF_8)
            val body = jsonBody.toRequestBody("application/json".toMediaType())
            val httpRequest = Request.Builder()
                .url(url)
                .post(body)
                .build()
            client.newCall(httpRequest).execute().use { response ->
                val text = response.body?.string().orEmpty()
                if (!response.isSuccessful) {
                    AppLog.w(TAG, "Feedback upload failed HTTP ${response.code}")
                    return@withContext Result.failure(IOException("HTTP ${response.code}"))
                }
                val decoded = runCatching { feedbackJson.decodeFromString<FeedbackResponse>(text) }
                    .getOrNull()
                when {
                    decoded?.ok == true -> Result.success(decoded.id ?: "ok")
                    decoded?.error != null -> Result.failure(IOException(decoded.error))
                    text.isBlank() -> Result.success("ok")
                    decoded?.id != null -> Result.success(decoded.id.orEmpty())
                    else -> Result.success("ok")
                }
            }
        } catch (e: Exception) {
            AppLog.w(TAG, "Feedback upload error: ${e.message}", e)
            Result.failure(e)
        }
    }
}
