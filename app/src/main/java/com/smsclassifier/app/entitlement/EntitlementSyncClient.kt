package com.smsclassifier.app.entitlement

import com.smsclassifier.app.BuildConfig
import com.smsclassifier.app.util.AppLog
import java.io.IOException
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody

private val entitlementJson = Json {
    ignoreUnknownKeys = true
    isLenient = true
}

@Serializable
data class EntitlementSyncRequest(
    val installId: String,
    val firebaseUid: String? = null
)

@Serializable
data class EntitlementSyncResponse(
    val ok: Boolean = false,
    val status: String = "unknown",
    val trialStartedAt: Long? = null,
    val trialExpiresAt: Long? = null,
    val trialActive: Boolean = false,
    val trialUsed: Boolean = false,
    val proActive: Boolean = false,
    val proExpiresAt: Long? = null
)

@Serializable
data class PurchaseVerifyRequest(
    val installId: String,
    val firebaseUid: String? = null,
    val packageName: String,
    val productId: String,
    val purchaseToken: String,
    val productType: String? = null
)

@Serializable
data class PurchaseVerifyResponse(
    val ok: Boolean = false,
    val status: String = "unknown",
    val validationStatus: String = "unknown",
    val trialStartedAt: Long? = null,
    val trialExpiresAt: Long? = null,
    val trialActive: Boolean = false,
    val trialUsed: Boolean = false,
    val proActive: Boolean = false,
    val proExpiresAt: Long? = null
)

class EntitlementSyncClient(
    private val baseUrl: String = BuildConfig.SERVER_API_BASE_URL
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(10L, TimeUnit.SECONDS)
        .readTimeout(10L, TimeUnit.SECONDS)
        .writeTimeout(10L, TimeUnit.SECONDS)
        .build()

    suspend fun fetch(installId: String, firebaseUid: String?): Result<EntitlementSyncResponse> =
        withContext(Dispatchers.IO) {
            try {
                val url = "${baseUrl.trimEnd('/')}/entitlements/me"
                    .toHttpUrl()
                    .newBuilder()
                    .addQueryParameter("installId", installId)
                    .apply {
                        if (!firebaseUid.isNullOrBlank()) {
                            addQueryParameter("firebaseUid", firebaseUid)
                        }
                    }
                    .build()
                val request = Request.Builder().url(url).get().build()
                client.newCall(request).execute().use { response ->
                    decodeResponse<EntitlementSyncResponse>(response.code, response.body?.string().orEmpty())
                }
            } catch (e: Exception) {
                AppLog.w(TAG, "Entitlement fetch failed: ${e.message}", e)
                Result.failure(e)
            }
        }

    suspend fun startTrial(installId: String, firebaseUid: String?): Result<EntitlementSyncResponse> =
        post(
            path = "trial/start",
            body = EntitlementSyncRequest(installId = installId, firebaseUid = firebaseUid)
        )

    suspend fun verifyPurchase(
        installId: String,
        firebaseUid: String?,
        packageName: String,
        productId: String,
        purchaseToken: String,
        productType: String? = null
    ): Result<PurchaseVerifyResponse> =
        post(
            path = "purchases/verify",
            body = PurchaseVerifyRequest(
                installId = installId,
                firebaseUid = firebaseUid,
                packageName = packageName,
                productId = productId,
                purchaseToken = purchaseToken,
                productType = productType
            )
        )

    private suspend inline fun <reified T> post(path: String, body: Any): Result<T> =
        withContext(Dispatchers.IO) {
            try {
                val url = "${baseUrl.trimEnd('/')}/$path"
                val jsonBody = when (body) {
                    is EntitlementSyncRequest -> entitlementJson.encodeToString(body)
                    is PurchaseVerifyRequest -> entitlementJson.encodeToString(body)
                    else -> error("Unsupported request type")
                }.toRequestBody("application/json".toMediaType())
                val request = Request.Builder()
                    .url(url)
                    .post(jsonBody)
                    .build()
                client.newCall(request).execute().use { response ->
                    decodeResponse<T>(response.code, response.body?.string().orEmpty())
                }
            } catch (e: Exception) {
                AppLog.w(TAG, "Entitlement POST $path failed: ${e.message}", e)
                Result.failure(e)
            }
        }

    private inline fun <reified T> decodeResponse(code: Int, body: String): Result<T> {
        if (code !in 200..299) {
            return Result.failure(IOException("HTTP $code"))
        }
        if (body.isBlank()) {
            return Result.failure(IOException("Empty entitlement response"))
        }
        return runCatching { entitlementJson.decodeFromString<T>(body) }
    }

    companion object {
        private const val TAG = "EntitlementSync"
    }
}
