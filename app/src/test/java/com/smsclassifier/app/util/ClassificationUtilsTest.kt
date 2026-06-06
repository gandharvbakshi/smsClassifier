package com.smsclassifier.app.util

import com.smsclassifier.app.data.MessageEntity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ClassificationUtilsTest {

    @Test
    fun humanizeIntent_knownIntent_returnsPlainOtpPurpose() {
        assertEquals(
            "Bank / card payment",
            ClassificationUtils.humanizeIntent("BANK_OR_CARD_TXN_OTP")
        )
        assertNull(ClassificationUtils.humanizeIntent("NOT_OTP"))
    }

    @Test
    fun extractOtpForCopy_userCorrectedNotOtp_hidesCopyValue() {
        val corrected = baseMessage(
            body = "Your OTP is 847291. Do not share it.",
            isOtp = false,
            userCorrected = true
        )

        assertFalse(ClassificationUtils.isOtpEffective(corrected))
        assertNull(ClassificationUtils.extractOtpForCopy(corrected))
    }

    @Test
    fun applyUserCorrection_actuallyOtp_makesCopyAvailable() {
        val corrected = ClassificationUtils.applyUserCorrection(
            baseMessage(
                body = "Your OTP is 847291. Do not share it.",
                isOtp = false,
                otpIntent = "NOT_OTP"
            ),
            "actually_otp"
        )

        assertTrue(corrected.userCorrected)
        assertTrue(ClassificationUtils.isOtpEffective(corrected))
        assertEquals("847291", ClassificationUtils.extractOtpForCopy(corrected))
        assertEquals("App action", ClassificationUtils.humanizeIntent(corrected.otpIntent))
    }

    @Test
    fun applyUserCorrection_notPhishing_clearsScamRisk() {
        val corrected = ClassificationUtils.applyUserCorrection(
            baseMessage(isPhishing = true, phishScore = 0.93f),
            "not_phishing"
        )

        assertTrue(corrected.userCorrected)
        assertFalse(corrected.isPhishing ?: true)
        assertEquals(0f, corrected.phishScore ?: -1f, 0f)
        assertNull(corrected.reasonsJson)
        assertEquals("No scam signs", ClassificationUtils.riskSummary(corrected))
    }

    private fun baseMessage(
        body: String = "Your OTP is 847291. Do not share it.",
        isOtp: Boolean? = true,
        otpIntent: String? = "APP_LOGIN_OTP",
        isPhishing: Boolean? = false,
        phishScore: Float? = 0f,
        userCorrected: Boolean = false,
        reasonsJson: String? = """["Old classifier reason"]"""
    ) = MessageEntity(
        sender = "VM-TEST",
        body = body,
        ts = 1L,
        isOtp = isOtp,
        otpIntent = otpIntent,
        isPhishing = isPhishing,
        phishScore = phishScore,
        userCorrected = userCorrected,
        reasonsJson = reasonsJson
    )
}
