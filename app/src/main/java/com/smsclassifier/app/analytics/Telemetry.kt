package com.smsclassifier.app.analytics

import android.content.Context
import android.os.Bundle
import com.google.firebase.analytics.FirebaseAnalytics
import com.smsclassifier.app.BuildConfig

class Telemetry(
    private val context: Context,
    private val consentManager: ConsentManager,
) {
    private val analytics get() = FirebaseAnalytics.getInstance(context)

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

    fun setUserProperty(name: String, value: String?) {
        if (!consentManager.analyticsEnabledNow()) return
        analytics.setUserProperty(name, value)
    }

    fun setUserId(uid: String?) {
        if (!consentManager.analyticsEnabledNow()) return
        analytics.setUserId(uid)
    }

    private fun validateParams(params: Map<String, Any?>) {
        val digitRun = Regex("\\d{4,}")
        val phoneish = Regex("\\+?\\d{10,}")
        val emailish = Regex("[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}")
        for ((k, v) in params) {
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
