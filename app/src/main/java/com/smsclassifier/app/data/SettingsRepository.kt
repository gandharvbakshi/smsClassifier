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

    /**
     * Anonymous per-install id. Prefers Firebase Installations id once available;
     * otherwise the legacy random UUID. Never show in user-facing UI.
     */
    val installId: String
        get() {
            val firebase = prefs.getString(KEY_FIREBASE_INSTALL_ID, null)
            if (!firebase.isNullOrBlank()) return firebase
            val existing = prefs.getString(KEY_INSTALL_ID, null)
            if (!existing.isNullOrBlank()) return existing
            val uuid = UUID.randomUUID().toString()
            prefs.edit().putString(KEY_INSTALL_ID, uuid).apply()
            return uuid
        }

    /**
     * Called from [com.smsclassifier.app.SMSClassifierApplication] after Firebase
     * Installations id is fetched. Preserves the pre-Firebase id as legacy.
     */
    fun applyFirebaseInstallId(firebaseId: String) {
        val before = prefs.getString(KEY_INSTALL_ID, null)
        if (before != null && prefs.getString(KEY_LEGACY_INSTALL_ID, null) == null) {
            prefs.edit().putString(KEY_LEGACY_INSTALL_ID, before).apply()
        }
        prefs.edit().putString(KEY_FIREBASE_INSTALL_ID, firebaseId).apply()
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

    fun clearFeedbackSettingsOnly() {
        prefs.edit()
            .remove(KEY_FEEDBACK_UPLOAD)
            .remove(KEY_FEEDBACK_CONSENT_ACK)
            .apply()
    }

    companion object {
        private const val PREFS_NAME = "sms_classifier_settings"
        private const val KEY_INSTALL_ID = "install_id_anonymous_v1"
        private const val KEY_FIREBASE_INSTALL_ID = "firebase_install_id"
        private const val KEY_LEGACY_INSTALL_ID = "legacy_install_id"
        private const val KEY_FEEDBACK_UPLOAD = "feedback_upload_enabled"
        private const val KEY_FEEDBACK_CONSENT_ACK = "feedback_consent_acknowledged"
        private const val KEY_NOTIFICATION_SOUND = "notification_sound_enabled"
        private const val KEY_NOTIFICATION_VIBRATION = "notification_vibration_enabled"
    }
}
