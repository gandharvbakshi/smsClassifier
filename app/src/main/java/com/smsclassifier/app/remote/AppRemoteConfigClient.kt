package com.smsclassifier.app.remote

import com.google.firebase.auth.FirebaseAuth
import com.smsclassifier.app.BuildConfig
import com.smsclassifier.app.util.AppLog
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.Json
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request

@Serializable
data class AppConfigResponse(
    val ok: Boolean = true,
    val maintenanceMode: Boolean = false,
    val installDisabled: Boolean = false,
    val serverClassifyEnabled: Boolean = true,
    val minVersionCode: Int? = null,
    val message: String? = null,
    val updateUrl: String? = null
)

data class RemoteSafetyState(
    val maintenanceMode: Boolean,
    val installDisabled: Boolean,
    val updateRequired: Boolean,
    val serverClassifyEnabled: Boolean,
    val message: String?,
    val updateUrl: String?
) {
    val blocksApp: Boolean
        get() = maintenanceMode || installDisabled || updateRequired

    companion object {
        fun allow(): RemoteSafetyState = RemoteSafetyState(
            maintenanceMode = false,
            installDisabled = false,
            updateRequired = false,
            serverClassifyEnabled = true,
            message = null,
            updateUrl = null
        )
    }
}

class AppRemoteConfigClient(
    private val baseUrl: String = BuildConfig.SERVER_API_BASE_URL
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(5L, TimeUnit.SECONDS)
        .readTimeout(5L, TimeUnit.SECONDS)
        .writeTimeout(5L, TimeUnit.SECONDS)
        .build()

    suspend fun fetch(installId: String): Result<RemoteSafetyState> = withContext(Dispatchers.IO) {
        try {
            val urlBuilder = "${baseUrl.trimEnd('/')}/config"
                .toHttpUrl()
                .newBuilder()
                .addQueryParameter("versionCode", BuildConfig.VERSION_CODE.toString())
                .addQueryParameter("versionName", BuildConfig.VERSION_NAME)
                .addQueryParameter("installId", installId)
            FirebaseAuth.getInstance().currentUser?.uid?.let { uid ->
                urlBuilder.addQueryParameter("firebaseUid", uid)
            }
            val url = urlBuilder.build()
            val request = Request.Builder().url(url).get().build()
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    return@withContext Result.failure(IllegalStateException("HTTP ${response.code}"))
                }
                val body = response.body?.string().orEmpty()
                val decoded = configJson.decodeFromString<AppConfigResponse>(body)
                val minCode = decoded.minVersionCode
                Result.success(
                    RemoteSafetyState(
                        maintenanceMode = decoded.maintenanceMode,
                        installDisabled = decoded.installDisabled,
                        updateRequired = minCode != null && BuildConfig.VERSION_CODE < minCode,
                        serverClassifyEnabled = decoded.serverClassifyEnabled,
                        message = decoded.message,
                        updateUrl = decoded.updateUrl
                    )
                )
            }
        } catch (e: Exception) {
            AppLog.w(TAG, "Remote config fetch failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    companion object {
        private const val TAG = "AppRemoteConfigClient"
        private val configJson = Json {
            ignoreUnknownKeys = true
            isLenient = true
        }
    }
}
