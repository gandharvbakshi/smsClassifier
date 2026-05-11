package com.smsclassifier.app.util

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

class SmsRedactorTest {

    @Test
    fun redact_sameBody_sameSalt_sameOutput() {
        val a = SmsRedactor.redactForTraining("Your code is 847291", "install-a")
        val b = SmsRedactor.redactForTraining("Your code is 847291", "install-a")
        assertEquals(a, b)
    }

    @Test
    fun redact_differentSalt_differentDigits() {
        val a = SmsRedactor.redactForTraining("OTP 999999", "salt1")
        val b = SmsRedactor.redactForTraining("OTP 999999", "salt2")
        assertNotEquals(a, b)
    }
}
