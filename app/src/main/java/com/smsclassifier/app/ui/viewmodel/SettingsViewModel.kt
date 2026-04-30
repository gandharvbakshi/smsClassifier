package com.smsclassifier.app.ui.viewmodel

import android.app.Activity
import android.app.role.RoleManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Telephony
import androidx.core.content.FileProvider
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.FeedbackEntity
import com.smsclassifier.app.data.SettingsRepository
import com.smsclassifier.app.util.BackendHealthChecker
import com.smsclassifier.app.util.PerformanceTracker
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import java.io.File

class SettingsViewModel(
    private val context: Context,
    private val database: AppDatabase
) : ViewModel() {
    private val settingsRepository = SettingsRepository(context)
    
    private val _isDefaultSmsApp = MutableStateFlow(checkIsDefaultSms())
    val isDefaultSmsApp: StateFlow<Boolean> = _isDefaultSmsApp.asStateFlow()
    
    private val _backendHealthStatus = MutableStateFlow<BackendHealthChecker.HealthStatus?>(null)
    val backendHealthStatus: StateFlow<BackendHealthChecker.HealthStatus?> = _backendHealthStatus.asStateFlow()
    
    private val _isCheckingBackendHealth = MutableStateFlow(false)
    val isCheckingBackendHealth: StateFlow<Boolean> = _isCheckingBackendHealth.asStateFlow()
    
    private val _performanceStats = MutableStateFlow<PerformanceTracker.PerformanceStats?>(null)
    val performanceStats: StateFlow<PerformanceTracker.PerformanceStats?> = _performanceStats.asStateFlow()

    private val _otpSelfTest = MutableStateFlow<OtpSelfTestResult?>(null)
    val otpSelfTest: StateFlow<OtpSelfTestResult?> = _otpSelfTest.asStateFlow()
    private val _isRunningSelfTest = MutableStateFlow(false)
    val isRunningSelfTest: StateFlow<Boolean> = _isRunningSelfTest.asStateFlow()

    /**
     * Snapshot of how OTP autofill plumbing looks on this device. Surfaced in
     * Settings → Diagnostics so the user can verify what other apps actually see.
     */
    data class OtpSelfTestResult(
        val isDefaultSms: Boolean,
        val systemInboxCount: Int,
        val ourDbCount: Int,
        val latestSystemInboxTs: Long?,
        val defaultSmsSubId: Int,
        val activeSubIds: List<Int>,
        val latestRowHasSubId: Boolean?,
        val latestRowHasProtocol: Boolean?,
        val canQueryInbox: Boolean,
        val canInsertProbe: Boolean,
        val errorMessage: String?
    )

    fun runOtpSelfTest() {
        if (_isRunningSelfTest.value) return
        viewModelScope.launch {
            _isRunningSelfTest.value = true
            try {
                _otpSelfTest.value = performOtpSelfTest()
            } finally {
                _isRunningSelfTest.value = false
            }
        }
    }

    private suspend fun performOtpSelfTest(): OtpSelfTestResult {
        val isDefault = checkIsDefaultSms()
        var canQuery = false
        var systemCount = 0
        var latestTs: Long? = null
        var latestHasSubId: Boolean? = null
        var latestHasProtocol: Boolean? = null
        var error: String? = null

        try {
            context.contentResolver.query(
                Telephony.Sms.Inbox.CONTENT_URI,
                arrayOf(
                    Telephony.Sms._ID,
                    Telephony.Sms.DATE,
                    Telephony.Sms.SUBSCRIPTION_ID,
                    Telephony.Sms.PROTOCOL
                ),
                null,
                null,
                "${Telephony.Sms.DATE} DESC LIMIT 1"
            )?.use { c ->
                canQuery = true
                if (c.moveToFirst()) {
                    val dateIdx = c.getColumnIndex(Telephony.Sms.DATE)
                    val subIdx = c.getColumnIndex(Telephony.Sms.SUBSCRIPTION_ID)
                    val protoIdx = c.getColumnIndex(Telephony.Sms.PROTOCOL)
                    if (dateIdx >= 0) latestTs = c.getLong(dateIdx)
                    if (subIdx >= 0) latestHasSubId = !c.isNull(subIdx) && c.getInt(subIdx) >= 0
                    if (protoIdx >= 0) latestHasProtocol = !c.isNull(protoIdx)
                }
            }

            // Count of all inbox rows.
            context.contentResolver.query(
                Telephony.Sms.Inbox.CONTENT_URI,
                arrayOf(Telephony.Sms._ID),
                null,
                null,
                null
            )?.use { c -> systemCount = c.count }
        } catch (t: Throwable) {
            error = "Query failed: ${t.message}"
        }

        // Probe-write a transient row to verify writes work end-to-end, then
        // immediately delete it. Only if we are the default SMS app — non-default
        // apps cannot insert anyway and would leave a confusing toast.
        var probeOk = false
        if (isDefault) {
            try {
                val now = System.currentTimeMillis()
                val v = android.content.ContentValues().apply {
                    put(Telephony.Sms.ADDRESS, "+0000000000")
                    put(Telephony.Sms.BODY, "[SMSClassifier self-test $now]")
                    put(Telephony.Sms.DATE, now)
                    put(Telephony.Sms.DATE_SENT, now)
                    put(Telephony.Sms.READ, 1)
                    put(Telephony.Sms.SEEN, 1)
                    put(Telephony.Sms.TYPE, Telephony.Sms.MESSAGE_TYPE_INBOX)
                }
                val uri = context.contentResolver.insert(Telephony.Sms.CONTENT_URI, v)
                if (uri != null) {
                    probeOk = true
                    context.contentResolver.delete(uri, null, null)
                }
            } catch (t: Throwable) {
                error = (error?.plus("; ") ?: "") + "Probe write failed: ${t.message}"
            }
        }

        val ourDbCount = try { database.messageDao().getAllMessages().size } catch (t: Throwable) { -1 }

        val defaultSubId = runCatching {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP_MR1)
                android.telephony.SubscriptionManager.getDefaultSmsSubscriptionId()
            else -1
        }.getOrDefault(-1)

        val activeSubs: List<Int> = runCatching {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP_MR1) {
                val sm = context.getSystemService(Context.TELEPHONY_SUBSCRIPTION_SERVICE)
                    as? android.telephony.SubscriptionManager
                sm?.activeSubscriptionInfoList?.map { it.subscriptionId } ?: emptyList()
            } else emptyList()
        }.getOrDefault(emptyList())

        return OtpSelfTestResult(
            isDefaultSms = isDefault,
            systemInboxCount = systemCount,
            ourDbCount = ourDbCount,
            latestSystemInboxTs = latestTs,
            defaultSmsSubId = defaultSubId,
            activeSubIds = activeSubs,
            latestRowHasSubId = latestHasSubId,
            latestRowHasProtocol = latestHasProtocol,
            canQueryInbox = canQuery,
            canInsertProbe = probeOk,
            errorMessage = error
        )
    }
    
    // Notification settings
    val notificationSoundEnabled: Boolean
        get() = settingsRepository.notificationSoundEnabled
    
    val notificationVibrationEnabled: Boolean
        get() = settingsRepository.notificationVibrationEnabled
    
    fun setNotificationSoundEnabled(enabled: Boolean) {
        settingsRepository.notificationSoundEnabled = enabled
    }
    
    fun setNotificationVibrationEnabled(enabled: Boolean) {
        settingsRepository.notificationVibrationEnabled = enabled
    }
    
    fun openNotificationSettings() {
        val intent = Intent(android.provider.Settings.ACTION_APP_NOTIFICATION_SETTINGS).apply {
            putExtra(android.provider.Settings.EXTRA_APP_PACKAGE, context.packageName)
        }
        context.startActivity(intent)
    }
    
    fun openNotificationChannelSettings() {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            val intent = Intent(android.provider.Settings.ACTION_CHANNEL_NOTIFICATION_SETTINGS).apply {
                putExtra(android.provider.Settings.EXTRA_APP_PACKAGE, context.packageName)
                putExtra(android.provider.Settings.EXTRA_CHANNEL_ID, "sms_notifications")
            }
            context.startActivity(intent)
        }
    }
    
    fun contactDeveloper() {
        val emailIntent = Intent(Intent.ACTION_SENDTO).apply {
            data = Uri.parse("mailto:")
            putExtra(Intent.EXTRA_EMAIL, arrayOf("gandharv@musicaigeneration.com"))
            putExtra(Intent.EXTRA_SUBJECT, "SMS Classifier App - Feedback")
            putExtra(Intent.EXTRA_TEXT, "Hi,\n\nI'd like to share some feedback about the SMS Classifier app:\n\n")
        }
        try {
            context.startActivity(Intent.createChooser(emailIntent, "Send feedback via email"))
        } catch (e: Exception) {
            // If no email app is available, try generic send intent
            val genericIntent = Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_EMAIL, arrayOf("gandharv@musicaigeneration.com"))
                putExtra(Intent.EXTRA_SUBJECT, "SMS Classifier App - Feedback")
                putExtra(Intent.EXTRA_TEXT, "Hi,\n\nI'd like to share some feedback about the SMS Classifier app:\n\n")
            }
            context.startActivity(Intent.createChooser(genericIntent, "Send feedback"))
        }
    }

    fun refreshDefaultSmsStatus() {
        _isDefaultSmsApp.value = checkIsDefaultSms()
    }

    fun createDefaultSmsIntent(): Intent? {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val roleManager = context.getSystemService(RoleManager::class.java)
            if (roleManager?.isRoleAvailable(RoleManager.ROLE_SMS) == true && !roleManager.isRoleHeld(RoleManager.ROLE_SMS)) {
                roleManager.createRequestRoleIntent(RoleManager.ROLE_SMS)
            } else {
                null
            }
        } else {
            val currentDefault = Telephony.Sms.getDefaultSmsPackage(context)
            if (currentDefault == context.packageName) {
                null
            } else {
                Intent(Telephony.Sms.Intents.ACTION_CHANGE_DEFAULT).apply {
                    putExtra(Telephony.Sms.Intents.EXTRA_PACKAGE_NAME, context.packageName)
                }
            }
        }
    }

    /** Last-known export error message. Surfaced as a snackbar by the UI. */
    private val _lastExportError = MutableStateFlow<String?>(null)
    val lastExportError: StateFlow<String?> = _lastExportError.asStateFlow()
    fun consumeExportError() { _lastExportError.value = null }

    /**
     * Quick label export — minimal columns for sharing labels.
     */
    fun exportLabels(onExported: (Uri?) -> Unit) {
        viewModelScope.launch {
            try {
                val messages = database.messageDao().getAllMessages()
                if (messages.isEmpty()) {
                    onExported(null)
                    return@launch
                }
                val file = File(context.getExternalFilesDir(null), "labels_export.csv")
                file.bufferedWriter().use { writer ->
                    writer.write("id,sender,body,timestamp,is_otp,otp_intent,is_phishing,phish_score,reviewed\n")
                    messages.forEach { msg ->
                        writer.write(
                            buildString {
                                append(msg.id).append(',')
                                append(csv(msg.sender)).append(',')
                                append(csv(msg.body)).append(',')
                                append(msg.ts).append(',')
                                append(msg.isOtp).append(',')
                                append(csv(msg.otpIntent ?: "")).append(',')
                                append(msg.isPhishing).append(',')
                                append(msg.phishScore ?: "").append(',')
                                append(msg.reviewed).append('\n')
                            }
                        )
                    }
                }
                onExported(fileUri(file))
            } catch (e: Exception) {
                _lastExportError.value = "Export failed: ${e.javaClass.simpleName}: ${e.message}"
                onExported(null)
            }
        }
    }

    /**
     * Full classification export — every message with all classification metadata,
     * the reasons JSON, plus all misclassification reports concatenated. Use this to
     * share data with the developer for debugging classifications.
     */
    fun exportFullClassificationData(onExported: (Uri?) -> Unit) {
        viewModelScope.launch {
            try {
                val messages = database.messageDao().getAllMessages()
                val logs = database.misclassificationLogDao().getAll().first()

                if (messages.isEmpty() && logs.isEmpty()) {
                    onExported(null)
                    return@launch
                }

                val timestamp = java.text.SimpleDateFormat("yyyyMMdd_HHmmss", java.util.Locale.US)
                    .format(java.util.Date())
                val file = File(
                    context.getExternalFilesDir(null),
                    "sms_classifier_export_$timestamp.csv"
                )

                file.bufferedWriter().use { writer ->
                    writer.write(
                        "section,id,message_id,sender,body,timestamp,thread_id,type," +
                            "is_otp,otp_intent,is_phishing,phish_score,reasons,reviewed,user_note\n"
                    )
                    messages.forEach { msg ->
                        writer.write(
                            buildString {
                                append("message,")
                                append(msg.id).append(',')
                                append(',')
                                append(csv(msg.sender)).append(',')
                                append(csv(msg.body)).append(',')
                                append(msg.ts).append(',')
                                append(msg.threadId).append(',')
                                append(msg.type).append(',')
                                append(msg.isOtp).append(',')
                                append(csv(msg.otpIntent ?: "")).append(',')
                                append(msg.isPhishing).append(',')
                                append(msg.phishScore ?: "").append(',')
                                append(csv(msg.reasonsJson ?: "")).append(',')
                                append(msg.reviewed).append(',')
                                append('\n')
                            }
                        )
                    }
                    logs.forEach { log ->
                        writer.write(
                            buildString {
                                append("misclassification,")
                                append(log.id).append(',')
                                append(log.messageId).append(',')
                                append(csv(log.sender)).append(',')
                                append(csv(log.body)).append(',')
                                append(log.createdAt).append(',')
                                append(',')
                                append(',')
                                append(log.predictedIsOtp).append(',')
                                append(csv(log.predictedOtpIntent ?: "")).append(',')
                                append(log.predictedIsPhishing).append(',')
                                append(',')
                                append(',')
                                append(',')
                                append(csv(log.userNote ?: "")).append('\n')
                            }
                        )
                    }
                }

                onExported(fileUri(file))
            } catch (e: Exception) {
                _lastExportError.value = "Export failed: ${e.javaClass.simpleName}: ${e.message}"
                onExported(null)
            }
        }
    }

    /**
     * Export only misclassification reports.
     */
    fun exportMisclassificationLogs(onExported: (Uri?) -> Unit) {
        viewModelScope.launch {
            try {
                val logs = database.misclassificationLogDao().getAll().first()
                if (logs.isEmpty()) {
                    onExported(null)
                    return@launch
                }
                val file = File(context.getExternalFilesDir(null), "misclassification_logs.csv")
                file.bufferedWriter().use { writer ->
                    writer.write(
                        "id,message_id,sender,body,predicted_is_otp,predicted_otp_intent," +
                            "predicted_is_phishing,reported_at,user_note\n"
                    )
                    logs.forEach { log ->
                        writer.write(
                            buildString {
                                append(log.id).append(',')
                                append(log.messageId).append(',')
                                append(csv(log.sender)).append(',')
                                append(csv(log.body)).append(',')
                                append(log.predictedIsOtp).append(',')
                                append(csv(log.predictedOtpIntent ?: "")).append(',')
                                append(log.predictedIsPhishing).append(',')
                                append(log.createdAt).append(',')
                                append(csv(log.userNote ?: "")).append('\n')
                            }
                        )
                    }
                }
                onExported(fileUri(file))
            } catch (e: Exception) {
                _lastExportError.value = "Export failed: ${e.javaClass.simpleName}: ${e.message}"
                onExported(null)
            }
        }
    }

    private fun csv(value: String): String {
        val escaped = value.replace("\"", "\"\"").replace("\n", " ").replace("\r", " ")
        return "\"$escaped\""
    }

    private fun fileUri(file: File): Uri = FileProvider.getUriForFile(
        context,
        "${context.packageName}.fileprovider",
        file
    )

    private fun checkIsDefaultSms(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val roleManager = context.getSystemService(RoleManager::class.java)
            roleManager?.isRoleHeld(RoleManager.ROLE_SMS) ?: false
        } else {
            Telephony.Sms.getDefaultSmsPackage(context) == context.packageName
        }
    }
    
    fun getProviderAuthority(): String {
        return "${context.packageName}.smsprovider"
    }
    
    fun isDefaultSmsHandler(): Boolean {
        return checkIsDefaultSms()
    }
    
    fun checkBackendHealth() {
        viewModelScope.launch {
            _isCheckingBackendHealth.value = true
            try {
                _backendHealthStatus.value = BackendHealthChecker.checkHealth()
            } catch (e: Exception) {
                _backendHealthStatus.value = BackendHealthChecker.HealthStatus(
                    isHealthy = false,
                    errorMessage = "Health check failed: ${e.message}"
                )
            } finally {
                _isCheckingBackendHealth.value = false
            }
        }
    }
    
    fun refreshPerformanceStats() {
        _performanceStats.value = PerformanceTracker.getStats(context)
    }
    
    fun clearPerformanceStats() {
        PerformanceTracker.clearStats(context)
        _performanceStats.value = PerformanceTracker.getStats(context)
    }
    
    init {
        // Check backend health on initialization
        checkBackendHealth()
        // Load performance stats
        refreshPerformanceStats()
    }
}

