package com.smsclassifier.app.ui.viewmodel

import android.app.Activity
import android.app.role.RoleManager
import android.content.Context
import android.content.SharedPreferences
import android.content.Intent
import android.os.Build
import android.provider.Telephony
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.FeedbackEntity
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.File

enum class InferenceMode {
    ON_DEVICE, SERVER
}

class SettingsViewModel(
    private val context: Context,
    private val database: AppDatabase,
    private val prefs: SharedPreferences
) : ViewModel() {
    private val _inferenceMode = MutableStateFlow(
        InferenceMode.valueOf(
            prefs.getString("inference_mode", InferenceMode.ON_DEVICE.name) ?: InferenceMode.ON_DEVICE.name
        )
    )
    val inferenceMode: StateFlow<InferenceMode> = _inferenceMode.asStateFlow()

    private val _isDefaultSmsApp = MutableStateFlow(checkIsDefaultSms())
    val isDefaultSmsApp: StateFlow<Boolean> = _isDefaultSmsApp.asStateFlow()

    fun setInferenceMode(mode: InferenceMode) {
        _inferenceMode.value = mode
        prefs.edit().putString("inference_mode", mode.name).apply()
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

    suspend fun exportLabels(): File {
        val feedback = database.feedbackDao().getAll()
        val file = File(context.getExternalFilesDir(null), "feedback_export.csv")
        
        file.bufferedWriter().use { writer ->
            writer.write("id,message_id,original_is_otp,original_otp_intent,original_is_phishing,original_phish_score,user_correction,timestamp\n")
            feedback.collect { feedbackList ->
                feedbackList.forEach { fb ->
                    writer.write("${fb.id},${fb.messageId},${fb.originalIsOtp},${fb.originalOtpIntent},${fb.originalIsPhishing},${fb.originalPhishScore},\"${fb.userCorrection}\",${fb.timestamp}\n")
                }
            }
        }
        
        return file
    }

    private fun checkIsDefaultSms(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val roleManager = context.getSystemService(RoleManager::class.java)
            roleManager?.isRoleHeld(RoleManager.ROLE_SMS) ?: false
        } else {
            Telephony.Sms.getDefaultSmsPackage(context) == context.packageName
        }
    }
}

