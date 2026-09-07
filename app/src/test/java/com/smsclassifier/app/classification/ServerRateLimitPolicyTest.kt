package com.smsclassifier.app.classification

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.After
import org.junit.Test
import java.time.Instant
import java.time.ZoneOffset
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

class ServerRateLimitPolicyTest {
    @After
    fun tearDown() {
        ServerRateLimitPolicy.resetForTests()
    }

    @Test
    fun parsesRetryAfterSecondsWithoutFloor() {
        val nowMs = 1_700_000_000_000L

        val retryAfterDelayMs = ServerRateLimitPolicy.parseRetryAfterDelayMs("5", nowMs)

        assertEquals(5_000L, retryAfterDelayMs)
    }

    @Test
    fun parsesRetryAfterDateHeader() {
        val nowMs = 1_700_000_000_000L
        val retryAfterAtMs = nowMs + 120_000L
        val header = ZonedDateTime.ofInstant(Instant.ofEpochMilli(retryAfterAtMs), ZoneOffset.UTC)
            .format(DateTimeFormatter.RFC_1123_DATE_TIME)

        assertEquals(120_000L, ServerRateLimitPolicy.parseRetryAfterDelayMs(header, nowMs))
    }

    @Test
    fun sharedCooldownBlocksSubsequentCallsUntilExpired() {
        ServerRateLimitPolicy.noteRateLimit(nowElapsedMs = 1_000L, retryAfterDelayMs = 120_000L)

        assertTrue(ServerRateLimitPolicy.isCooldownActive(1_001L))
        assertTrue(ServerRateLimitPolicy.isCooldownActive(61_000L))
        assertFalse(ServerRateLimitPolicy.isCooldownActive(121_001L))
    }

    @Test
    fun laterShorterCooldownDoesNotShortenAnActiveOne() {
        ServerRateLimitPolicy.noteRateLimit(nowElapsedMs = 1_000L, retryAfterDelayMs = 120_000L)
        ServerRateLimitPolicy.noteRateLimit(nowElapsedMs = 2_000L, retryAfterDelayMs = 5_000L)

        assertTrue(ServerRateLimitPolicy.isCooldownActive(120_999L))
        assertFalse(ServerRateLimitPolicy.isCooldownActive(121_001L))
    }
}
