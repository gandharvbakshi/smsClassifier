package com.smsclassifier.app.classification

/**
 * Local heuristic-only path used when the user is not entitled to server inference
 * (free tier after trial expiry, or before first OTP has started the trial).
 */
class HeuristicOnlyClassifier : Classifier {

    override suspend fun predict(input: MessageFeatures): Prediction {
        val h = HeuristicOtpClassifier.classify(input.text, input.sender)
        return Prediction(
            isOtp = h.isOtp,
            otpIntent = null,
            isPhishing = null,
            phishScore = 0f,
            reasons = emptyList(),
            inferenceTimeMs = 0L
        )
    }

    override fun isAvailable(): Boolean = true
}
