package com.smsclassifier.app.classification

data class Prediction(
    val isOtp: Boolean?,
    val otpIntent: String?,
    val isPhishing: Boolean?,
    val phishScore: Float, // 0.0 to 1.0
    val reasons: List<String> = emptyList(),
    val inferenceTimeMs: Long = 0
)

