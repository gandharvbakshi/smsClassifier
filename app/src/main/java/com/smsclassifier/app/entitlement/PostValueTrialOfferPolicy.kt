package com.smsclassifier.app.entitlement

object PostValueTrialOfferPolicy {
    const val MAX_IMPRESSIONS = 2
    const val COOLDOWN_MS = 3L * 24L * 60L * 60L * 1000L

    fun shouldShow(
        classifiedMessageCount: Int,
        isPaidPro: Boolean,
        hasTrialStarted: Boolean,
        impressionCount: Int,
        nextEligibleAtMs: Long,
        nowMs: Long,
    ): Boolean {
        return classifiedMessageCount > 0 &&
            !isPaidPro &&
            !hasTrialStarted &&
            impressionCount < MAX_IMPRESSIONS &&
            nowMs >= nextEligibleAtMs
    }

    fun nextEligibleAt(nowMs: Long): Long = nowMs + COOLDOWN_MS
}

