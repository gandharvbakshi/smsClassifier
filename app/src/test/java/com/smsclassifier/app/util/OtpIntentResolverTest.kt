package com.smsclassifier.app.util

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class OtpIntentResolverTest {

    @Test
    fun bankTransaction_hasSpecificPurposeAndNeverShareGuidance() {
        val presentation = OtpIntentResolver.resolve("BANK_OR_CARD_TXN_OTP")

        assertEquals("Bank transaction OTP", presentation.label)
        assertEquals("Never share this OTP", presentation.safetyMessage)
        assertEquals(OtpSharingGuidance.NEVER_SHARE, presentation.sharingGuidance)
    }

    @Test
    fun courier_hasOnlyCourierGuidance() {
        val presentation = OtpIntentResolver.resolve("DELIVERY_OR_SERVICE_OTP")

        assertEquals("Courier delivery OTP", presentation.label)
        assertEquals("Share only with your courier", presentation.safetyMessage)
        assertEquals(OtpSharingGuidance.COURIER_ONLY, presentation.sharingGuidance)
    }

    @Test
    fun whatsAppContext_usesWhatsAppSpecificAccountChangeLabel() {
        val presentation = OtpIntentResolver.resolve(
            otpIntent = "APP_ACCOUNT_CHANGE_OTP",
            sender = "VM-WHATSAPP",
            body = "Use 834291 on your new phone"
        )

        assertEquals("WhatsApp account change OTP", presentation.label)
        assertEquals("Never share this OTP", presentation.safetyMessage)
    }

    @Test
    fun missingIntent_usesHeuristicThenFallsBackExactlyToOtp() {
        val inferred = OtpIntentResolver.resolve(
            otpIntent = null,
            sender = "JX-PORTER-S",
            body = "Give delivery code 537993 to your courier"
        )
        val uncertain = OtpIntentResolver.resolve(otpIntent = null)

        assertEquals("Courier delivery OTP", inferred.label)
        assertEquals("OTP", uncertain.label)
        assertNull(uncertain.safetyMessage)
    }

    @Test
    fun genericStoredIntent_isRefinedWhenMessageHasClearPurpose() {
        val presentation = OtpIntentResolver.resolve(
            otpIntent = "GENERIC_APP_ACTION_OTP",
            sender = "JX-PORTER-S",
            body = "Give delivery code 537993 to your courier"
        )

        assertEquals("Courier delivery OTP", presentation.label)
        assertEquals("Share only with your courier", presentation.safetyMessage)
    }

    @Test
    fun talkBackDescription_readsDigitsAndRelevantGuidance() {
        val description = OtpIntentResolver.talkBackDescription(
            presentation = OtpIntentResolver.resolve("APP_LOGIN_OTP"),
            senderName = "Google",
            code = "481902"
        )

        assertEquals(
            "App login OTP from Google. 4 8 1 9 0 2. Never share this OTP. Double tap to copy OTP.",
            description
        )
    }
}
