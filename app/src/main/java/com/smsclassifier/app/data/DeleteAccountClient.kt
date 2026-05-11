package com.smsclassifier.app.data

import com.smsclassifier.app.BuildConfig
import com.smsclassifier.app.util.AppLog
import java.io.IOException
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request

class DeleteAccountClient(
    private val baseUrl: String = BuildConfig.SERVER_API_BASE_URL
) {

    private val client = OkHttpClient.Builder()
        .connectTimeout(10L, TimeUnit.SECONDS)
        .readTimeout(10L, TimeUnit.SECONDS)
        .writeTimeout(10L, TimeUnit.SECONDS)
        .build()

    suspend fun delete(installId: String, uid: String?): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val encInstall = URLEncoder.encode(installId, StandardCharsets.UTF_8)
            val q = buildString {
                append("/users/me?installId=").append(encInstall)
                if (!uid.isNullOrBlank()) {
                    append("&uid=").append(URLEncoder.encode(uid, StandardCharsets.UTF_8))
                }
            }
            val url = baseUrl.trimEnd('/') + q
            val request = Request.Builder()
                .url(url)
                .delete()
                .addHeader("Authorization", "Bearer $installId")
                .build()
            client.newCall(request).execute().use { response ->
                when (response.code) {
                    200, 204, 404 -> Result.success(Unit)
                    in 500..599 -> Result.failure(IOException("Server error HTTP ${response.code}"))
                    else -> Result.failure(IOException("HTTP ${response.code}"))
                }
            }
        } catch (e: Exception) {
            AppLog.w(TAG, "delete account: ${e.message}", e)
            Result.failure(e)
        }
    }

    companion object {
        private const val TAG = "DeleteAccountClient"
    }
}
