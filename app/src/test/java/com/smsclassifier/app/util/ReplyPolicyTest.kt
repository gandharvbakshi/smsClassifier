package com.smsclassifier.app.util

import com.smsclassifier.app.data.MessageEntity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ReplyPolicyTest {
    @Test
    fun acceptsOrdinaryLocalAndInternationalNumbers() {
        assertEquals("+919876543210", ReplyPolicy.recipient(" +91 98765-43210 "))
        assertEquals("4155550123", ReplyPolicy.recipient("(415) 555-0123"))
        assertEquals("5550123", ReplyPolicy.recipient("555.0123"))
    }

    @Test
    fun rejectsBrandedSendersAndUnknownAddresses() {
        listOf("VM-SBIOTP", "AD-HDFCBK-S", "AX-1234567890-T", "AMAZON", "UNKNOWN", "").forEach {
            assertNull(it, ReplyPolicy.recipient(it))
        }
    }

    @Test
    fun rejectsShortCodesAndNonPhoneDialStrings() {
        listOf("12345", "123456", "+1234567", "*123456789#", "555-0123 ext 1", "+0123456789").forEach {
            assertNull(it, ReplyPolicy.recipient(it))
        }
    }

    @Test
    fun requiresDeliberateConfirmationForFlaggedOrSuspiciousMessages() {
        val normal = MessageEntity(sender = "+14155550123", body = "On my way", ts = 1L)
        assertFalse(ReplyPolicy.requiresConfirmation(normal))
        assertFalse(ReplyPolicy.requiresConfirmation(normal.copy(phishScore = 0.29f)))
        assertTrue(ReplyPolicy.requiresConfirmation(normal.copy(phishScore = 0.3f)))
        assertTrue(ReplyPolicy.requiresConfirmation(normal.copy(isPhishing = true)))
    }

    @Test
    fun routesEligibleSendersAndKeepsFlaggedRepliesBehindConfirmation() {
        val phone = MessageEntity(sender = "+14155550123", body = "On my way", ts = 1L)
        assertEquals(ReplyPolicy.Route.COMPOSER, ReplyPolicy.route(phone))
        assertEquals(ReplyPolicy.Route.CONFIRM, ReplyPolicy.route(phone.copy(phishScore = 0.3f)))
        assertEquals(ReplyPolicy.Route.CONFIRM, ReplyPolicy.route(phone.copy(isPhishing = true)))
        assertNull(ReplyPolicy.route(phone.copy(sender = "VM-SBIOTP")))
        assertNull(ReplyPolicy.route(phone.copy(sender = "12345")))
    }
}
