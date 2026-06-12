package com.smsclassifier.app.classification

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class HeuristicOtpClassifierTest {

    @Test
    fun classify_plainOtpFromKnownSender_detectsOtpWithIntent() {
        val result = HeuristicOtpClassifier.classify(
            text = "Your login OTP is 847291. Do not share it with anyone.",
            sender = "VM-GOOGLE"
        )

        assertTrue(result.isOtp)
        assertTrue(result.confidence > 0.8f)
        assertEquals("APP_LOGIN_OTP", result.suggestedIntent)
    }

    @Test
    fun classify_otpWithLink_reducesConfidenceAndExplainsRisk() {
        val plain = HeuristicOtpClassifier.classify(
            text = "Your OTP is 847291. Do not share it with anyone.",
            sender = "VM-GOOGLE"
        )
        val withLink = HeuristicOtpClassifier.classify(
            text = "Your OTP is 847291. Do not share it. Verify now at https://example-login.test",
            sender = "VM-GOOGLE"
        )

        assertTrue(withLink.isOtp)
        assertTrue(withLink.confidence < plain.confidence)
        assertTrue(withLink.reasons.any { it.contains("Contains link") })
    }

    @Test
    fun classify_transactionMessageWithDigits_doesNotBecomeOtp() {
        val result = HeuristicOtpClassifier.classify(
            text = "INR 8472.91 spent on your card XX1234 at STORE. Avl limit INR 10000.",
            sender = "VM-ICICIT"
        )

        assertFalse(result.isOtp)
        assertEquals(0f, result.confidence)
    }
}
