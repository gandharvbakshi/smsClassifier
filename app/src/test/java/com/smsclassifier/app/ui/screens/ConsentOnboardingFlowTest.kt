package com.smsclassifier.app.ui.screens

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ConsentOnboardingFlowTest {

    @Test
    fun successfulTrialAppliesConsentBeforeStartAndThenCompletesOnboarding() = runBlocking {
        val calls = mutableListOf<String>()

        val started = runConsentAwareTrialStart(
            applyConsent = { calls += "consent" },
            startTrial = {
                calls += "trial"
                true
            },
            completeOnboarding = { calls += "complete" }
        )

        assertTrue(started)
        assertEquals(listOf("consent", "trial", "complete"), calls)
    }

    @Test
    fun failedTrialAppliesConsentButDoesNotCompleteOnboarding() = runBlocking {
        val calls = mutableListOf<String>()

        val started = runConsentAwareTrialStart(
            applyConsent = { calls += "consent" },
            startTrial = {
                calls += "trial"
                false
            },
            completeOnboarding = { calls += "complete" }
        )

        assertFalse(started)
        assertEquals(listOf("consent", "trial"), calls)
    }
}
