package com.smsclassifier.app.analytics

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MonetizationTelemetryPolicyTest {

    @Test
    fun safe_label_sanitizes_and_caps_values() {
        assertEquals("otp_fraud_warning", MonetizationTelemetryPolicy.safeLabel("OTP Fraud Warning!"))
        assertEquals("unknown", MonetizationTelemetryPolicy.safeLabel("   "))
        assertEquals(
            "very_long_label_that_gets_trimmed_at_the",
            MonetizationTelemetryPolicy.safeLabel("Very long label that gets trimmed at the forty character mark!")
        )
    }

    @Test
    fun trial_start_params_are_sanitized() {
        val params = MonetizationTelemetryPolicy.trialStartAttemptParams(
            source = "Paywall CTA",
            trigger = "Start Trial!"
        )

        assertEquals("paywall_cta", params["source"])
        assertEquals("start_trial", params["trigger"])
    }

    @Test
    fun trial_start_result_params_include_reason_only_when_present() {
        val withReason = MonetizationTelemetryPolicy.trialStartResultParams(
            source = "Paywall CTA",
            trigger = "Start Trial!",
            outcome = "Started",
            reason = "backend unavailable"
        )
        val withoutReason = MonetizationTelemetryPolicy.trialStartResultParams(
            source = "Paywall CTA",
            trigger = "Start Trial!",
            outcome = "Started",
            reason = null
        )

        assertEquals("paywall_cta", withReason["source"])
        assertEquals("start_trial", withReason["trigger"])
        assertEquals("started", withReason["outcome"])
        assertEquals("backend_unavailable", withReason["reason"])
        assertFalse(withoutReason.containsKey("reason"))
    }

    @Test
    fun sha256_fingerprint_is_stable_and_fixed_length() {
        assertEquals(
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            MonetizationTelemetryPolicy.sha256Fingerprint("abc")
        )
        assertEquals(64, MonetizationTelemetryPolicy.sha256Fingerprint("purchase-token").length)
    }

    @Test
    fun purchase_verified_emission_is_one_shot_per_fingerprint() {
        assertTrue(MonetizationTelemetryPolicy.shouldEmitPurchaseVerified(null, "abc"))
        assertFalse(MonetizationTelemetryPolicy.shouldEmitPurchaseVerified("abc", "abc"))
        assertTrue(MonetizationTelemetryPolicy.shouldEmitPurchaseVerified("abc", "def"))
    }
}
