package com.smsclassifier.app.util

import android.content.Context
import com.google.firebase.crashlytics.FirebaseCrashlytics
import com.smsclassifier.app.AppContainer

/**
 * Phase 4 — Crashlytics custom keys after consent is evaluated.
 */
object CrashlyticsBootstrap {

    fun setUserId(uid: String?) {
        if (uid.isNullOrBlank()) return
        if (!AppContainer.consentManager.crashlyticsEnabledNow()) return
        FirebaseCrashlytics.getInstance().setUserId(uid)
    }

    fun refresh(context: Context, isDefaultSms: Boolean) {
        if (!AppContainer.consentManager.crashlyticsEnabledNow()) return
        val crash = FirebaseCrashlytics.getInstance()
        crash.setCustomKey("default_sms", isDefaultSms.toString())
        crash.setCustomKey("inference_mode", AppContainer.entitlementManager.crashlyticsInferenceLabel())
        val prefs = context.getSharedPreferences("telemetry_launch", Context.MODE_PRIVATE)
        val firstOpen = prefs.getLong("first_open_at_ms", System.currentTimeMillis())
        val ageDays = ((System.currentTimeMillis() - firstOpen) / 86_400_000L).coerceAtLeast(0)
        crash.setCustomKey("install_age_days", ageDays.toInt())
    }
}
