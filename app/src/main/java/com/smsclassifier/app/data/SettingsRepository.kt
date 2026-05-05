package com.smsclassifier.app.data

import android.content.Context
import android.content.SharedPreferences
import java.util.UUID

/**
 * Repository for app settings stored in SharedPreferences.
 */
class SettingsRepository(context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences(
        PREFS_NAME,
        Context.MODE_PRIVATE
    )

    /** Anonymous per-install id for aggregating telemetry; never logged to user-facing UI. */
    val installId: String
        get() {
            val existing = prefs.getString(KEY_INSTALL_ID, null)
            if (!existing.isNullOrBlank()) return existing
            val uuid = UUID.randomUUID().toString()
            prefs.edit().putString(KEY_INSTALL_ID, uuid).apply()
            return uuid
        }

    var feedbackUploadEnabled: Boolean
        get() = prefs.getBoolean(KEY_FEEDBACK_UPLOAD, false)
        set(value) = prefs.edit().putBoolean(KEY_FEEDBACK_UPLOAD, value).apply()

    var feedbackConsentAcknowledged: Boolean
        get() = prefs.getBoolean(KEY_FEEDBACK_CONSENT_ACK, false)
        set(value) = prefs.edit().putBoolean(KEY_FEEDBACK_CONSENT_ACK, value).apply()

    // Notification settings
    var notificationSoundEnabled: Boolean
        get() = prefs.getBoolean(KEY_NOTIFICATION_SOUND, true)
        set(value) = prefs.edit().putBoolean(KEY_NOTIFICATION_SOUND, value).apply()

    var notificationVibrationEnabled: Boolean
        get() = prefs.getBoolean(KEY_NOTIFICATION_VIBRATION, true)
        set(value) = prefs.edit().putBoolean(KEY_NOTIFICATION_VIBRATION, value).apply()

    companion object {
        private const val PREFS_NAME = "sms_classifier_settings"
        private const val KEY_INSTALL_ID = "install_id_anonymous_v1"
        private const val KEY_FEEDBACK_UPLOAD = "feedback_upload_enabled"
        private const val KEY_FEEDBACK_CONSENT_ACK = "feedback_consent_acknowledged"
        private const val KEY_NOTIFICATION_SOUND = "notification_sound_enabled"
        private const val KEY_NOTIFICATION_VIBRATION = "notification_vibration_enabled"
    }
}
