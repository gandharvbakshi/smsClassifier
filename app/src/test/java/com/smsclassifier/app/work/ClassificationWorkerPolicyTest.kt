package com.smsclassifier.app.work

import com.smsclassifier.app.classification.Prediction
import com.smsclassifier.app.data.MessageEntity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ClassificationWorkerPolicyTest {

    @Test
    fun fallbackMessageLeavesUnclassifiedQueue() {
        val message = baseMessage()
        val heuristicPrediction = Prediction(
            isOtp = false,
            otpIntent = null,
            isPhishing = null,
            phishScore = 0f
        )

        val fallback = ClassificationWorkerPolicy.fallbackPrediction(
            heuristicPrediction,
            ClassificationWorkerPolicy.OFFLINE_FALLBACK_REASON
        )
        val updated = ClassificationWorkerPolicy.updatedMessage(
            message = message,
            prediction = fallback,
            usedServerResult = false
        )

        assertEquals(false, updated.isOtp)
        assertNull(updated.isPhishing)
        assertNull(updated.phishScore)
        assertEquals("[]", updated.linkVerdictsJson)
        assertTrue(updated.reviewed)
        assertNotNull(updated.reasonsJson)
        assertFalse(matchesUnclassifiedPredicate(updated))
    }

    @Test
    fun serverResultPersistsRiskFieldsAndMarksReviewed() {
        val message = baseMessage()
        val serverPrediction = Prediction(
            isOtp = true,
            otpIntent = "APP_LOGIN_OTP",
            isPhishing = false,
            phishScore = 0.1f,
            reasons = listOf("server ok")
        )

        val updated = ClassificationWorkerPolicy.updatedMessage(
            message = message,
            prediction = serverPrediction,
            usedServerResult = true
        )

        assertEquals(true, updated.isOtp)
        assertEquals("APP_LOGIN_OTP", updated.otpIntent)
        assertEquals(false, updated.isPhishing)
        assertEquals(0.1f, updated.phishScore ?: -1f, 0.0001f)
        assertEquals("[]", updated.linkVerdictsJson)
        assertTrue(updated.reviewed)
        assertFalse(matchesUnclassifiedPredicate(updated))
    }

    @Test
    fun localResultPersistsPurposeButNotCloudRiskFields() {
        val updated = ClassificationWorkerPolicy.updatedMessage(
            message = baseMessage(),
            prediction = Prediction(
                isOtp = true,
                otpIntent = "DELIVERY_OR_SERVICE_OTP",
                isPhishing = null,
                phishScore = 0f
            ),
            usedServerResult = false
        )

        assertEquals(true, updated.isOtp)
        assertEquals("DELIVERY_OR_SERVICE_OTP", updated.otpIntent)
        assertNull(updated.isPhishing)
        assertNull(updated.phishScore)
        assertFalse(matchesUnclassifiedPredicate(updated))
    }

    @Test
    fun intentBackfillPreservesExistingCloudRiskAndLinkVerdicts() {
        val message = baseMessage().copy(
            isOtp = true,
            otpIntent = null,
            isPhishing = true,
            phishScore = 0.91f,
            linkVerdictsJson = "[{\"status\":\"unsafe\"}]",
            reviewed = true
        )

        val updated = ClassificationWorkerPolicy.updatedMessage(
            message = message,
            prediction = Prediction(
                isOtp = true,
                otpIntent = "APP_LOGIN_OTP",
                isPhishing = null,
                phishScore = 0f
            ),
            usedServerResult = false
        )

        assertEquals("APP_LOGIN_OTP", updated.otpIntent)
        assertEquals(true, updated.isPhishing)
        assertEquals(0.91f, updated.phishScore ?: -1f, 0.0001f)
        assertEquals("[{\"status\":\"unsafe\"}]", updated.linkVerdictsJson)
        assertFalse(matchesUnclassifiedPredicate(updated))
    }

    @Test
    fun intentBackfillDoesNotDemoteExistingOtpWhenLocalFallbackMissesIt() {
        val message = baseMessage().copy(
            isOtp = true,
            otpIntent = null,
            isPhishing = false,
            phishScore = 0.08f,
            reviewed = true
        )

        val updated = ClassificationWorkerPolicy.updatedMessage(
            message = message,
            prediction = Prediction(
                isOtp = false,
                otpIntent = null,
                isPhishing = null,
                phishScore = 0f
            ),
            usedServerResult = false
        )

        assertEquals(true, updated.isOtp)
        assertEquals("GENERIC_APP_ACTION_OTP", updated.otpIntent)
        assertEquals(false, updated.isPhishing)
        assertEquals(0.08f, updated.phishScore ?: -1f, 0.0001f)
        assertFalse(matchesUnclassifiedPredicate(updated))
    }

    @Test
    fun serverRiskOnlyResultKeepsHeuristicOtpPurpose() {
        val merged = ClassificationWorkerPolicy.mergeServerWithHeuristic(
            serverPrediction = Prediction(
                isOtp = null,
                otpIntent = null,
                isPhishing = false,
                phishScore = 0.05f
            ),
            heuristicPrediction = Prediction(
                isOtp = true,
                otpIntent = "APP_LOGIN_OTP",
                isPhishing = null,
                phishScore = 0f
            )
        )

        assertEquals(true, merged.isOtp)
        assertEquals("APP_LOGIN_OTP", merged.otpIntent)
        assertEquals(false, merged.isPhishing)
    }

    @Test
    fun otpWithoutSpecificIntent_getsExactGenericFallbackAndLeavesBackfillQueue() {
        val updated = ClassificationWorkerPolicy.updatedMessage(
            message = baseMessage(),
            prediction = Prediction(
                isOtp = true,
                otpIntent = null,
                isPhishing = false,
                phishScore = 0.1f
            ),
            usedServerResult = true
        )

        assertEquals("GENERIC_APP_ACTION_OTP", updated.otpIntent)
        assertFalse(matchesUnclassifiedPredicate(updated))
    }

    @Test
    fun reasonsJsonEscapesQuotesAndBackslashes() {
        val json = ClassificationWorkerPolicy.reasonsJson(
            listOf("Cloud said \"busy\"", "path C:\\tmp")
        )

        assertEquals("[\"Cloud said \\\"busy\\\"\",\"path C:\\\\tmp\"]", json)
    }

    private fun baseMessage(): MessageEntity {
        return MessageEntity(
            id = 7L,
            sender = "TEST",
            body = "hello",
            ts = 1_700_000_000_000L,
            reviewed = false,
            isOtp = null,
            isPhishing = null,
            phishScore = null
        )
    }

    private fun matchesUnclassifiedPredicate(message: MessageEntity): Boolean {
        return message.isOtp == null ||
            (message.isOtp == true && message.otpIntent == null && !message.userCorrected) ||
            (!message.reviewed && (message.isPhishing == null || message.phishScore == null))
    }
}
