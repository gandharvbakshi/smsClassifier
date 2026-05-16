package com.smsclassifier.app.analytics

import android.content.Context
import android.os.Bundle
import com.google.firebase.analytics.FirebaseAnalytics
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.BuildConfig
import java.time.Instant
import java.time.ZoneOffset

class Telemetry(
    private val context: Context,
    private val consentManager: ConsentManager,
) {
    private val analytics get() = FirebaseAnalytics.getInstance(context)

    private val launchPrefs get() =
        context.getSharedPreferences("telemetry_launch", Context.MODE_PRIVATE)

    fun init() {
        analytics.setAnalyticsCollectionEnabled(consentManager.analyticsEnabledNow())
        analytics.setUserProperty("app_version_name", BuildConfig.VERSION_NAME)
        analytics.setUserProperty("app_version_code", BuildConfig.VERSION_CODE.toString())
    }

    fun logEvent(name: String, params: Map<String, Any?> = emptyMap()) {
        if (!consentManager.analyticsEnabledNow()) return
        if (BuildConfig.DEBUG) validateParams(params)
        val bundle = Bundle()
        for ((k, v) in params) {
            when (v) {
                null -> {}
                is String -> bundle.putString(k, v)
                is Int -> bundle.putLong(k, v.toLong())
                is Long -> bundle.putLong(k, v)
                is Double -> bundle.putDouble(k, v)
                is Float -> bundle.putDouble(k, v.toDouble())
                is Boolean -> bundle.putString(k, v.toString())
                else -> bundle.putString(k, v.toString())
            }
        }
        analytics.logEvent(name, bundle)
    }

    fun logScreenView(route: String) {
        logEvent("screen_view", mapOf("screen_name" to screenName(route)))
    }

    fun logCtaTap(surface: String, action: String) {
        logEvent(
            "cta_tap",
            mapOf("surface" to safeLabel(surface), "action" to safeLabel(action))
        )
    }

    fun logMessageOpen(surface: String) {
        logEvent("message_open", mapOf("surface" to safeLabel(surface)))
    }

    fun logOtpCopied(surface: String) {
        logEvent("otp_copied", mapOf("surface" to safeLabel(surface)))
    }

    fun logFilterChanged(filter: String) {
        logEvent("filter_changed", mapOf("filter" to safeLabel(filter)))
    }

    fun logSearchUsed(surface: String) {
        logEvent("search_used", mapOf("surface" to safeLabel(surface)))
    }

    fun setUserProperty(name: String, value: String?) {
        if (!consentManager.analyticsEnabledNow()) return
        analytics.setUserProperty(name, value)
    }

    fun setUserId(uid: String?) {
        if (!consentManager.analyticsEnabledNow()) return
        analytics.setUserId(uid)
    }

    /**
     * Call from [com.smsclassifier.app.MainActivity] on resume: rate-limited [app_open],
     * once-per-UTC-day [daily_active], and [default_sms_set] on transition to default.
     */
    fun onMainActivityResume(defaultSmsNow: Boolean) {
        if (!consentManager.analyticsEnabledNow()) return
        val now = System.currentTimeMillis()
        val firstOpen = launchPrefs.getLong("first_open_at_ms", now)
        val ageDays = ((now - firstOpen) / 86_400_000L).coerceAtLeast(0L)
        setUserProperty("entitlement_state", AppContainer.entitlementManager.telemetryEntitlementLabel())
        setUserProperty("default_sms", if (defaultSmsNow) "true" else "false")
        setUserProperty("app_install_age_days", ageDays.toString())

        val lastOpen = launchPrefs.getLong("last_app_open_event_ts", 0L)
        if (now - lastOpen >= 60_000L) {
            logEvent("app_open")
            launchPrefs.edit().putLong("last_app_open_event_ts", now).apply()
        }

        val utcDay = Instant.ofEpochMilli(now).atZone(ZoneOffset.UTC).toLocalDate().toString()
        val lastDau = launchPrefs.getString("last_dau_date", null)
        if (lastDau != utcDay) {
            logEvent("daily_active", mapOf("dau_date" to utcDay))
            launchPrefs.edit().putString("last_dau_date", utcDay).apply()
        }

        val prevDefault = launchPrefs.getBoolean("last_known_default_sms", defaultSmsNow)
        if (defaultSmsNow && !prevDefault) {
            logEvent("default_sms_set")
        }
        launchPrefs.edit().putBoolean("last_known_default_sms", defaultSmsNow).apply()
    }

    /** First successfully classified SMS (one-shot). */
    fun maybeLogFirstSmsClassified() {
        if (!consentManager.analyticsEnabledNow()) return
        if (launchPrefs.getBoolean("first_sms_classified_done", false)) return
        logEvent("first_sms_classified")
        launchPrefs.edit().putBoolean("first_sms_classified_done", true).apply()
    }

    fun logNotificationPermission(granted: Boolean) {
        logEvent(
            if (granted) "permission_post_notifications_granted"
            else "permission_post_notifications_denied"
        )
    }

    fun logConsentChanged(kind: String, value: Boolean) {
        logEvent(
            "consent_changed",
            mapOf("consent_kind" to kind, "value" to value.toString())
        )
    }

    private fun safeLabel(value: String): String {
        return value
            .lowercase()
            .replace(Regex("[^a-z0-9_]+"), "_")
            .trim('_')
            .take(40)
            .ifBlank { "unknown" }
    }

    private fun screenName(route: String): String {
        return when {
            route == "detail/{messageId}" || route.startsWith("detail/") -> "detail"
            route == "thread/{threadId}" || route.startsWith("thread/") -> "thread"
            route == "paywall/{trigger}" || route.startsWith("paywall/") -> "paywall"
            else -> safeLabel(route)
        }
    }

    private fun validateParams(params: Map<String, Any?>) {
        val digitRun = Regex("\\d{4,}")
        val phoneish = Regex("\\+?\\d{10,}")
        val emailish = Regex("[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}")
        val allowedDigitHeavyKeys = setOf(
            "seconds_since_first_open",
            "app_install_age_days",
            "score",
            "value",
            "dau_date",
            "uploaded",
            "failed"
        )
        for ((k, v) in params) {
            if (k in allowedDigitHeavyKeys) continue
            val s = v?.toString() ?: continue
            if (digitRun.containsMatchIn(s) || phoneish.containsMatchIn(s) || emailish.containsMatchIn(s)) {
                throw IllegalArgumentException("Telemetry param may contain PII: key=$k")
            }
        }
    }

    companion object {
        @JvmField
        var instance: Telemetry? = null
    }
}
