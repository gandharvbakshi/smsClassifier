package com.smsclassifier.app.ui.screens

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class TrialNudgeCopyTest {
    @Test
    fun `five day copy uses benefit counts when scams were caught`() {
        val copy = trialNudgeCopy(5, 5, 42, 7, 1, "₹499/year")

        assertEquals("Trial ends in 5 days", copy.title)
        assertEquals("Pro sorted 42 messages and caught 1 scam text.", copy.body)
        assertEquals("Keep Pro — ₹499/year", copy.primaryText)
    }

    @Test
    fun `five day copy never reports zero scams`() {
        val copy = trialNudgeCopy(5, 5, 42, 7, 0, null)

        assertEquals("Your Pro trial ends in 5 days.", copy.body)
        assertFalse(copy.body.contains("0 scams"))
        assertEquals("Keep Pro", copy.primaryText)
    }

    @Test
    fun `three day copy handles singular OTP`() {
        val copy = trialNudgeCopy(3, 3, 8, 1, 0, "₹499/year")

        assertEquals("3 days left — Pro found 1 OTP for you.", copy.body)
    }

    @Test
    fun `one day copy says today and keeps scam benefit`() {
        val copy = trialNudgeCopy(1, 1, 0, 0, 0, "₹499/year")

        assertEquals("Trial ends today", copy.title)
        assertEquals("Last day of Pro. Keep scam alerts working after today.", copy.body)
    }

    @Test
    fun `late five day milestone uses actual four days remaining`() {
        val copy = trialNudgeCopy(5, 4, 0, 0, 0, null)

        assertEquals("Trial ends in 4 days", copy.title)
        assertEquals("Your Pro trial ends in 4 days.", copy.body)
    }

    @Test
    fun `late three day milestone uses actual two days remaining`() {
        val copy = trialNudgeCopy(3, 2, 8, 1, 0, null)

        assertEquals("Trial ends in 2 days", copy.title)
        assertEquals("2 days left — Pro found 1 OTP for you.", copy.body)
    }
}
