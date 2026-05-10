package com.smsclassifier.app.entitlement

import android.content.Context
import com.google.firebase.crashlytics.FirebaseCrashlytics
import com.smsclassifier.app.analytics.Telemetry

class EntitlementManager(private val context: Context) {

    private val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun isPro(now: Long = System.currentTimeMillis()): Boolean {
        if (prefs.getBoolean(KEY_PRO, false)) return true
        val started = prefs.getLong(KEY_TRIAL_START, -1L)
        if (started <= 0L) return false
        return now - started < TRIAL_MS
    }

    fun onWorkerDetectedOtp() {
        if (prefs.getBoolean(KEY_PRO, false)) {
            refreshCrashlyticsMode()
            return
        }
        if (prefs.getLong(KEY_TRIAL_START, -1L) <= 0L) {
            prefs.edit().putLong(KEY_TRIAL_START, System.currentTimeMillis()).apply()
            Telemetry.instance?.logEvent("trial_started")
        }
        if (!prefs.getBoolean(KEY_FIRST_OTP_EVENT, false)) {
            prefs.edit().putBoolean(KEY_FIRST_OTP_EVENT, true).apply()
            val launchPrefs = context.getSharedPreferences("telemetry_launch", Context.MODE_PRIVATE)
            val firstOpen = launchPrefs.getLong("first_open_at_ms", System.currentTimeMillis())
            val seconds = (System.currentTimeMillis() - firstOpen) / 1000L
            Telemetry.instance?.logEvent(
                "first_otp_detected",
                mapOf("seconds_since_first_open" to seconds)
            )
        }
        refreshCrashlyticsMode()
    }

    fun setProPurchased(purchased: Boolean) {
        prefs.edit().putBoolean(KEY_PRO, purchased).apply()
        refreshCrashlyticsMode()
    }

    private fun refreshCrashlyticsMode() {
        val mode = when {
            prefs.getBoolean(KEY_PRO, false) -> "pro"
            isPro() -> "trial"
            else -> "free"
        }
        FirebaseCrashlytics.getInstance().setCustomKey("inference_mode", mode)
    }

    init {
        refreshCrashlyticsMode()
    }

    companion object {
        private const val PREFS_NAME = "entitlement_prefs"
        private const val KEY_PRO = "pro_purchased"
        private const val KEY_TRIAL_START = "trial_started_at_ms"
        private const val KEY_FIRST_OTP_EVENT = "first_otp_event_sent"
        private val TRIAL_MS = 7L * 24 * 60 * 60 * 1000
    }
}
