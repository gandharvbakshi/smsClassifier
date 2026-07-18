package com.smsclassifier.app.ui.screens

data class TrialNudgeCopy(
    val title: String,
    val body: String,
    val primaryText: String,
)

fun trialNudgeCopy(
    milestone: Int,
    daysRemaining: Int,
    classifiedMessageCount: Int,
    otpMessageCount: Int,
    phishingMessageCount: Int,
    formattedPrice: String?,
): TrialNudgeCopy {
    require(milestone in setOf(5, 3, 1)) { "Unsupported trial nudge milestone: $milestone" }
    require(daysRemaining in 1..milestone) {
        "Days remaining must be within the milestone window: $daysRemaining/$milestone"
    }

    val title = if (daysRemaining == 1) "Trial ends today" else "Trial ends in $daysRemaining days"
    val body = when (milestone) {
        5 -> if (classifiedMessageCount > 0 && phishingMessageCount > 0) {
            val scamLabel = if (phishingMessageCount == 1) "scam text" else "scam texts"
            "Pro sorted $classifiedMessageCount messages and caught $phishingMessageCount $scamLabel."
        } else {
            "Your Pro trial ends in $daysRemaining days."
        }

        3 -> if (otpMessageCount > 0) {
            val otpLabel = if (otpMessageCount == 1) "OTP" else "OTPs"
            "$daysRemaining days left — Pro found $otpMessageCount $otpLabel for you."
        } else {
            "$daysRemaining days of Pro left."
        }

        else -> "Last day of Pro. Keep scam alerts working after today."
    }
    val primaryText = formattedPrice
        ?.takeIf { it.isNotBlank() }
        ?.let { "Keep Pro — $it" }
        ?: "Keep Pro"

    return TrialNudgeCopy(title = title, body = body, primaryText = primaryText)
}
