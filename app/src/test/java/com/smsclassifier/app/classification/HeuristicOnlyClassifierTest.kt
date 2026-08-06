package com.smsclassifier.app.classification

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class HeuristicOnlyClassifierTest {

    @Test
    fun predict_keepsLocalOtpPurposeWithoutCloudRiskFields() = runBlocking {
        val prediction = HeuristicOnlyClassifier().predict(
            MessageFeatures(
                text = "Your delivery OTP is 537993. Share it with your courier only.",
                sender = "JX-PORTER-S"
            )
        )

        assertTrue(prediction.isOtp == true)
        assertEquals("DELIVERY_OR_SERVICE_OTP", prediction.otpIntent)
        assertNull(prediction.isPhishing)
    }
}
