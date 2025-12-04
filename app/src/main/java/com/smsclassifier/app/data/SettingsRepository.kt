package com.smsclassifier.app.data

import android.content.Context
import android.content.SharedPreferences

/**
 * Repository for app settings stored in SharedPreferences.
 */
class SettingsRepository(context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences(
        PREFS_NAME,
        Context.MODE_PRIVATE
    )
    
    // Notification settings
    var notificationSoundEnabled: Boolean
        get() = prefs.getBoolean(KEY_NOTIFICATION_SOUND, true)
        set(value) = prefs.edit().putBoolean(KEY_NOTIFICATION_SOUND, value).apply()
    
    var notificationVibrationEnabled: Boolean
        get() = prefs.getBoolean(KEY_NOTIFICATION_VIBRATION, true)
        set(value) = prefs.edit().putBoolean(KEY_NOTIFICATION_VIBRATION, value).apply()
    
    companion object {
        private const val PREFS_NAME = "sms_classifier_settings"
        private const val KEY_NOTIFICATION_SOUND = "notification_sound_enabled"
        private const val KEY_NOTIFICATION_VIBRATION = "notification_vibration_enabled"
    }
}

