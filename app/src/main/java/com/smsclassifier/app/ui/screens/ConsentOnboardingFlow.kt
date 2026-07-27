package com.smsclassifier.app.ui.screens

internal suspend fun runConsentAwareTrialStart(
    applyConsent: suspend () -> Unit,
    startTrial: suspend () -> Boolean,
    completeOnboarding: suspend () -> Unit
): Boolean {
    applyConsent()
    if (!startTrial()) {
        return false
    }
    completeOnboarding()
    return true
}
