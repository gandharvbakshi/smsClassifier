package com.smsclassifier.app.entitlement

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PostValueTrialOfferPolicyTest {
    @Test
    fun shows_only_after_first_classified_message_for_free_trial_eligible_user() {
        assertFalse(shouldShow(classified = 0))
        assertTrue(shouldShow(classified = 1))
        assertFalse(shouldShow(classified = 1, paid = true))
        assertFalse(shouldShow(classified = 1, trialStarted = true))
    }

    @Test
    fun enforces_cooldown_and_two_impression_cap() {
        val now = 1_000_000L
        assertFalse(shouldShow(classified = 1, impressions = 1, nextEligibleAt = now + 1, now = now))
        assertTrue(shouldShow(classified = 1, impressions = 1, nextEligibleAt = now, now = now))
        assertFalse(shouldShow(classified = 1, impressions = 2, nextEligibleAt = 0, now = now))
        assertTrue(PostValueTrialOfferPolicy.nextEligibleAt(now) > now)
    }

    private fun shouldShow(
        classified: Int,
        paid: Boolean = false,
        trialStarted: Boolean = false,
        impressions: Int = 0,
        nextEligibleAt: Long = 0,
        now: Long = 1_000_000L,
    ): Boolean = PostValueTrialOfferPolicy.shouldShow(
        classifiedMessageCount = classified,
        isPaidPro = paid,
        hasTrialStarted = trialStarted,
        impressionCount = impressions,
        nextEligibleAtMs = nextEligibleAt,
        nowMs = now,
    )
}

