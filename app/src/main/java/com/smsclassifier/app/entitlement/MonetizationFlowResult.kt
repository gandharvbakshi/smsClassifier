package com.smsclassifier.app.entitlement

data class RemoteTrialStartResult(
    val source: String,
    val trigger: String,
    val started: Boolean,
    val outcome: String,
    val reason: String? = null,
    val trialActive: Boolean = false,
    val trialStartedAt: Long? = null,
)

data class PurchaseGrantResult(
    val granted: Boolean,
    val backendVerified: Boolean,
    val provisional: Boolean,
    val tokenFingerprint: String,
    val reason: String? = null,
)
