package com.smsclassifier.app.util

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SmsRedactorTest {

    @Test
    fun redact_sameBody_sameSalt_sameOutput() {
        val a = SmsRedactor.redactForTraining("Your code is 847291", "install-a")
        val b = SmsRedactor.redactForTraining("Your code is 847291", "install-a")
        assertEquals(a, b)
    }

    @Test
    fun redact_differentSalt_differentTokens() {
        val a = SmsRedactor.redactForTraining("OTP 999999", "salt1")
        val b = SmsRedactor.redactForTraining("OTP 999999", "salt2")
        assertNotEquals(a, b)
        assertTrue(a.contains("<DIGITS:6:"))
        assertFalse(Regex("\\b\\d{4,}\\b").containsMatchIn(a))
    }

    @Test
    fun redact_masksUrlsEmailsAndLongDigitRuns() {
        val redacted = SmsRedactor.redactForTraining(
            "OTP 847291 for +91 9876543210. Visit https://bad.example/pay?m=1234 or mail a@b.co",
            "install-a"
        )

        assertTrue(redacted.contains("<URL:"))
        assertTrue(redacted.contains("<EMAIL:"))
        assertTrue(redacted.contains("<DIGITS:6:"))
        assertTrue(redacted.contains("<DIGITS:10:"))
        assertFalse(redacted.contains("847291"))
        assertFalse(redacted.contains("9876543210"))
        assertFalse(redacted.contains("https://bad.example"))
        assertFalse(redacted.contains("a@b.co"))
    }

    @Test
    fun redact_masksBareDomainsIncludingPathsAndQueries() {
        val redacted = SmsRedactor.redactForTraining(
            "Track at example.com/pay?token=private123 and demo.example:8/order#status",
            "install-a"
        )

        assertEquals(2, Regex("<URL:[a-z]+>").findAll(redacted).count())
        assertFalse(redacted.contains("example.com"))
        assertFalse(redacted.contains("demo.example"))
        assertFalse(redacted.contains("private123"))
    }

    @Test
    fun redactSender_masksNumericSenderButKeepsDltSender() {
        val masked = SmsRedactor.redactSenderForTraining("+91 9876543210", "install-a")

        assertTrue(masked.startsWith("<SENDER:"))
        assertEquals("VM-ICICIT-S", SmsRedactor.redactSenderForTraining("VM-ICICIT-S", "install-a"))
    }
}
