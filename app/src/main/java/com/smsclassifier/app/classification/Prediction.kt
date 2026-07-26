package com.smsclassifier.app.classification

import kotlinx.serialization.Serializable

@Serializable
data class LinkVerdict(
    val url: String,
    val host: String,
    val status: String,
    val threatTypes: List<String> = emptyList(),
    val checkedAtEpochMs: Long? = null,
    val latencyMs: Float = 0f
)

data class Prediction(
    val isOtp: Boolean?,
    val otpIntent: String?,
    val isPhishing: Boolean?,
    val phishScore: Float, // 0.0 to 1.0
    val reasons: List<String> = emptyList(),
    val linkVerdicts: List<LinkVerdict> = emptyList(),
    val inferenceTimeMs: Long = 0
)

