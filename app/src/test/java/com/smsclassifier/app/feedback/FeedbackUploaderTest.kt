package com.smsclassifier.app.feedback

import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import org.junit.Assert.assertTrue
import org.junit.Test

class FeedbackUploaderTest {

    @Test
    fun feedbackRequest_serializesCorrectedOtpIntent() {
        val json = Json.encodeToString(
            FeedbackRequest(
                installId = "install-123",
                appVersionCode = 45,
                appVersionName = "1.2.20",
                sender = "VM-TEST",
                body = "Your OTP is 847291.",
                userCorrection = "Wrong OTP purpose",
                correctedOtpIntent = "UPI_TXN_OR_PIN_OTP",
                clientCreatedAt = 1_700_000_000_000L
            )
        )

        assertTrue(json.contains("\"correctedOtpIntent\":\"UPI_TXN_OR_PIN_OTP\""))
    }
}
