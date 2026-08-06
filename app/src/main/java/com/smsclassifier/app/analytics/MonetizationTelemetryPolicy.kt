package com.smsclassifier.app.analytics

import java.security.MessageDigest

object MonetizationTelemetryPolicy {
    private val nonLabelChars = Regex("[^a-z0-9_]+")

    fun safeLabel(value: String?): String {
        return value
            .orEmpty()
            .lowercase()
            .replace(nonLabelChars, "_")
            .trim('_')
            .take(40)
            .ifBlank { "unknown" }
    }

    fun trialStartAttemptParams(source: String, trigger: String): Map<String, String> {
        return mapOf(
            "source" to safeLabel(source),
            "trigger" to safeLabel(trigger)
        )
    }

    fun trialStartResultParams(
        source: String,
        trigger: String,
        outcome: String,
        reason: String?
    ): Map<String, String> {
        return buildMap {
            put("source", safeLabel(source))
            put("trigger", safeLabel(trigger))
            put("outcome", safeLabel(outcome))
            reason?.let { put("reason", safeLabel(it)) }
        }
    }

    fun sha256Fingerprint(value: String): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(value.toByteArray(Charsets.UTF_8))
        return digest.joinToString("") { byte -> "%02x".format(byte) }
    }

    fun shouldEmitPurchaseVerified(lastFingerprint: String?, currentFingerprint: String): Boolean {
        return lastFingerprint != currentFingerprint
    }
}
