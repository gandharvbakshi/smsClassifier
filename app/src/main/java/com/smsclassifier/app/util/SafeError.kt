package com.smsclassifier.app.util

import com.google.firebase.crashlytics.FirebaseCrashlytics
import com.smsclassifier.app.AppContainer

/**
 * Strip obvious PII patterns before Crashlytics logs; gate recording on crash consent.
 */
object SafeError {

    fun redactMessage(message: String): String {
        var s = message
        s = Regex("\\b\\d{4,}\\b").replace(s, "<digits>")
        s = Regex("\\+?\\d[\\d\\s-]{8,}\\d").replace(s, "<phone>")
        s = Regex("[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}").replace(s, "<email>")
        return s
    }

    fun report(tag: String, throwable: Throwable, contextMessage: String? = null) {
        if (!AppContainer.consentManager.crashlyticsEnabledNow()) return
        val crash = FirebaseCrashlytics.getInstance()
        crash.log("[$tag] ${contextMessage?.let { redactMessage(it) } ?: ""}")
        crash.recordException(throwable)
    }
}
