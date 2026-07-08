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
        assertTrue(updated.reviewed)
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
            (!message.reviewed && (message.isPhishing == null || message.phishScore == null))
    }
}
