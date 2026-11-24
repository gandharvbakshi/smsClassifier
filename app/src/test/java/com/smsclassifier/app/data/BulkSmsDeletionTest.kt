package com.smsclassifier.app.data

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BulkSmsDeletionTest {
    @Test
    fun conversationSnapshotLeavesNewAndUnselectedMessagesAlone() = runBlocking {
        val first = sms(1, 10)
        val second = sms(2, 10)
        val third = sms(3, 20)
        val later = sms(4, 10)
        val elsewhere = sms(5, 30)
        val plan = BulkSmsDeletePlan(conversations = true, messages = listOf(first, second, third))
        val local = listOf(first, second, third, later, elsewhere).associateBy { it.id }.toMutableMap()
        val provider = mutableListOf<Long>()

        val result = executeBulkSmsDelete(plan, local::get, { provider += it.id }, { local.remove(it.id) == it })

        assertEquals(2, plan.conversationCount)
        assertEquals(3, plan.messages.size)
        assertEquals(BulkSmsDeleteResult(3, 0, 0), result)
        assertEquals(listOf(1L, 2L, 3L), provider)
        assertEquals(setOf(later.id, elsewhere.id), local.keys)
    }

    @Test
    fun providerFailureAndReusedAppIdKeepLocalRecordsWhileOtherRowsProceed() = runBlocking {
        val denied = sms(1, 10)
        val replaced = sms(2, 10)
        val gone = sms(3, 10)
        val succeeded = sms(4, 10)
        val replacement = replaced.copy(body = "A different text")
        val local = listOf(denied, replacement, succeeded).associateBy { it.id }.toMutableMap()
        val provider = mutableListOf<Long>()
        val plan = BulkSmsDeletePlan(false, listOf(denied, replaced, gone, succeeded))

        val result = executeBulkSmsDelete(
            plan,
            local::get,
            {
                provider += it.id
                if (it == denied) throw SecurityException()
            },
            { local.remove(it.id) == it }
        )

        assertEquals(BulkSmsDeleteResult(1, 1, 2), result)
        assertEquals(listOf(denied.id, succeeded.id), provider)
        assertEquals(listOf(denied, replacement), local.values.toList())
    }

    @Test
    fun localFailureAfterProviderDeletionCanBeRetried() = runBlocking {
        val selected = sms(1, 10)
        val plan = BulkSmsDeletePlan(false, listOf(selected))
        val provider = mutableSetOf(selected.id)
        val local = mutableMapOf(selected.id to selected)

        val first = executeBulkSmsDelete(plan, local::get, { provider.remove(it.id) }, { false })
        val retry = executeBulkSmsDelete(plan, local::get, { provider.remove(it.id) }, { local.remove(it.id) == it })

        assertEquals(BulkSmsDeleteResult(0, 0, 1), first)
        assertEquals(BulkSmsDeleteResult(1, 0, 0), retry)
        assertTrue(local.isEmpty())
        assertTrue(provider.isEmpty())
    }

    @Test
    fun providerFingerprintBindsProviderIdAndNeverUsesTheAppId() {
        val linked = sms(9, 20).copy(providerId = 42)
        val (linkedSelection, linkedArgs) = providerFingerprint(linked)
        val (legacySelection, legacyArgs) = providerFingerprint(linked.copy(providerId = null))

        assertTrue(linkedSelection.startsWith("_id = ?"))
        assertFalse(legacySelection.contains("_id"))
        assertEquals(listOf("42", "+123456789", "A selected text", "1234", "1"), linkedArgs.toList())
        assertEquals(linkedArgs.drop(1), legacyArgs.toList())
    }

    private fun sms(id: Long, thread: Long) = SmsDeletionIdentity(
        id, thread, "+123456789", "A selected text", 1234, 1, null
    )
}
