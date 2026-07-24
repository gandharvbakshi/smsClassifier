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
            "Bank or card payment",
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
        assertEquals("Other app action", ClassificationUtils.humanizeIntent(corrected.otpIntent))
    }

    @Test
    fun applyUserCorrection_otherWithExplicitIntent_setsOtpPurpose() {
        val corrected = ClassificationUtils.applyUserCorrection(
            baseMessage(
                body = "Your OTP is 847291. Do not share it.",
                isOtp = false,
                otpIntent = "NOT_OTP"
            ),
            "other",
            correctedOtpIntent = "UPI_TXN_OR_PIN_OTP"
        )

        assertTrue(corrected.userCorrected)
        assertTrue(ClassificationUtils.isOtpEffective(corrected))
        assertEquals("UPI_TXN_OR_PIN_OTP", corrected.otpIntent)
        assertEquals("UPI payment or PIN", ClassificationUtils.humanizeIntent(corrected.otpIntent))
    }

    @Test
    fun applyUserCorrection_otherWithoutIntent_preservesLegacyNullBehavior() {
        val corrected = ClassificationUtils.applyUserCorrection(
            baseMessage(
                body = "Your OTP is 847291. Do not share it.",
                isOtp = false,
                otpIntent = "NOT_OTP"
            ),
            "other"
        )

        assertTrue(corrected.userCorrected)
        assertFalse(ClassificationUtils.isOtpEffective(corrected))
        assertEquals("NOT_OTP", corrected.otpIntent)
    }

    @Test
    fun shouldWarnOnOtpNotification_bankAndUpiContexts_returnTrue() {
        assertTrue(
            ClassificationUtils.shouldWarnOnOtpNotification(
                body = "Your SBI UPI PIN is 482917. Do not share it.",
                sender = "VM-SBIOTP",
                otpIntent = "UPI_TXN_OR_PIN_OTP"
            )
        )
        assertTrue(
            ClassificationUtils.shouldWarnOnOtpNotification(
                body = "Your ICICI card OTP is 928411. Do not share it.",
                sender = "VM-ICICIT",
                otpIntent = "BANK_OR_CARD_TXN_OTP"
            )
        )
        assertTrue(
            ClassificationUtils.shouldWarnOnOtpNotification(
                body = "Your login code is 665411. Do not share this OTP with anyone.",
                sender = "VM-GOOGLE",
                otpIntent = "APP_LOGIN_OTP"
            )
        )
    }

    @Test
    fun shouldWarnOnOtpNotification_deliveryOtpAndPin_returnFalse() {
        assertFalse(
            ClassificationUtils.shouldWarnOnOtpNotification(
                body = "Your delivery OTP is 482917. Share it with the delivery partner only.",
                sender = "VM-SWIGGY",
                otpIntent = "DELIVERY_OR_SERVICE_OTP"
            )
        )
        assertFalse(
            ClassificationUtils.shouldWarnOnOtpNotification(
                body = "Your delivery PIN is 7712. Do not share it with anyone.",
                sender = "VM-ZOMATO",
                otpIntent = "DELIVERY_OR_SERVICE_OTP"
            )
        )
    }

    @Test
    fun extractOtpForCopy_amountBeforeOtp_usesActualOtp() {
        val message = baseMessage(
            body = "OTP for txn of INR 4200 at AMAZON is 482917. Valid for 10 min. Do not share with anyone.",
            sender = "VK-SBIOTP",
            otpIntent = "BANK_OR_CARD_TXN_OTP"
        )

        assertEquals("482917", ClassificationUtils.extractOtpForCopy(message))
    }

    @Test
    fun extractOtpForCopy_porterDeliveryCode_exposesProminentCode() {
        val message = baseMessage(
            body = "Your rider is out for delivery. Please give the Delivery Code - 537993, to receive your Porter order.",
            sender = "JX-PORTER-S",
            otpIntent = "DELIVERY_OR_SERVICE_OTP"
        )

        assertEquals("537993", ClassificationUtils.extractOtpForCopy(message))
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
        assertEquals("Very low", ClassificationUtils.riskSummary(corrected))
    }

    @Test
    fun riskSummary_highRisk_returnsPlainWordLabel() {
        val message = baseMessage(isPhishing = true, phishScore = 0.91f)

        assertEquals(ClassificationUtils.RiskLevel.HIGH, ClassificationUtils.detailRiskLevel(message))
        assertEquals("High", ClassificationUtils.riskSummary(message))
    }

    @Test
    fun plainReasons_mapsRawClassifierReasonsToUserLanguage() {
        val reasons = ClassificationUtils.plainReasons(
            baseMessage(),
            listOf(
                "Numeric code found (4-8 digits)",
                "Heuristic OTP vetting",
                "Known bank sender ID"
            )
        )

        assertTrue(reasons.contains("Contains a short OTP that expires soon"))
        assertTrue(reasons.contains("Wording matches a login or payment OTP"))
        assertTrue(reasons.contains("Sent from a registered sender ID"))
    }

    @Test
    fun plainReasons_safeMessageProvidesDefaultUserReasons() {
        val reasons = ClassificationUtils.plainReasons(
            baseMessage(
                body = "USD 11.80 spent using ICICI Bank Card XX7007.",
                isOtp = false,
                otpIntent = "NOT_OTP",
                isPhishing = false,
                phishScore = 0.01f
            ),
            emptyList()
        )

        assertTrue(reasons.contains("Reads like a normal transaction alert"))
        assertTrue(reasons.contains("Does not look like an OTP request"))
    }

    @Test
    fun plainReasons_safeMessageDoesNotShowOtpReasonsFromRawClassifier() {
        val reasons = ClassificationUtils.plainReasons(
            baseMessage(
                body = "USD 11.80 spent using ICICI Bank Card XX7007.",
                isOtp = false,
                otpIntent = "NOT_OTP",
                isPhishing = false,
                phishScore = 0.01f
            ),
            listOf(
                "Numeric code found (4-8 digits)",
                "Heuristic OTP vetting",
                "Transaction/marketing context"
            )
        )

        assertFalse(reasons.contains("Contains a short OTP that expires soon"))
        assertFalse(reasons.contains("Wording matches a login or payment OTP"))
        assertTrue(reasons.contains("Reads like a normal transaction alert"))
    }

    private fun baseMessage(
        body: String = "Your OTP is 847291. Do not share it.",
        sender: String = "VM-TEST",
        isOtp: Boolean? = true,
        otpIntent: String? = "APP_LOGIN_OTP",
        isPhishing: Boolean? = false,
        phishScore: Float? = 0f,
        userCorrected: Boolean = false,
        reasonsJson: String? = """["Old classifier reason"]"""
    ) = MessageEntity(
        sender = sender,
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
