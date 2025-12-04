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
                        writer.write("${msg.id},\"${msg.sender}\",\"${msg.body.replace("\"", "\"\"")}\",${msg.ts},${msg.isOtp},${msg.otpIntent ?: ""},${msg.isPhishing},${msg.phishScore ?: ""},${msg.reviewed}\n")
                    }
                }
                
                val uri = FileProvider.getUriForFile(
                    context,
                    "${context.packageName}.fileprovider",
                    file
                )
                onExported(uri)
            } catch (e: Exception) {
                onExported(null)
            }
        }
    }

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
}

