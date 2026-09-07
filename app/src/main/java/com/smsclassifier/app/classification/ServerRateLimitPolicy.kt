package com.smsclassifier.app.classification

import android.os.SystemClock
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicLong

object ServerRateLimitPolicy {
    private const val DEFAULT_SHARED_COOLDOWN_MS = 60_000L
    private const val MAX_SHARED_COOLDOWN_MS = 15 * 60_000L

    private val cooldownUntilElapsedMs = AtomicLong(0L)

    fun isCooldownActive(nowElapsedMs: Long = SystemClock.elapsedRealtime()): Boolean {
        return nowElapsedMs < cooldownUntilElapsedMs.get()
    }

    fun remainingCooldownMs(nowElapsedMs: Long = SystemClock.elapsedRealtime()): Long {
        return (cooldownUntilElapsedMs.get() - nowElapsedMs).coerceAtLeast(0L)
    }

    fun noteRateLimit(
        nowElapsedMs: Long = SystemClock.elapsedRealtime(),
        retryAfterDelayMs: Long? = null
    ) {
        val nextCooldownUntilElapsedMs =
            nowElapsedMs + resolveCooldownDelayMs(retryAfterDelayMs)
        cooldownUntilElapsedMs.updateAndGet { current ->
            maxOf(current, nextCooldownUntilElapsedMs)
        }
    }

    fun resetForTests() {
        cooldownUntilElapsedMs.set(0L)
    }

    fun parseRetryAfterDelayMs(retryAfterHeader: String?, nowMs: Long): Long? {
        val header = retryAfterHeader?.trim()?.takeIf { it.isNotEmpty() } ?: return null
        header.toLongOrNull()?.let { seconds ->
            return if (seconds <= 0L) {
                null
            } else {
                val boundedSeconds = seconds.coerceAtMost(MAX_SHARED_COOLDOWN_MS / 1_000L)
                TimeUnit.SECONDS.toMillis(boundedSeconds)
            }
        }

        val dateTime = runCatching {
            ZonedDateTime.parse(header, DateTimeFormatter.RFC_1123_DATE_TIME).toInstant().toEpochMilli()
        }.getOrNull()

        val delayMs = dateTime?.let { it - nowMs } ?: return null
        return if (delayMs <= 0L) {
            null
        } else {
            delayMs.coerceAtMost(MAX_SHARED_COOLDOWN_MS)
        }
    }

    fun resolveCooldownDelayMs(retryAfterDelayMs: Long?): Long {
        return retryAfterDelayMs?.coerceAtMost(MAX_SHARED_COOLDOWN_MS)
            ?: DEFAULT_SHARED_COOLDOWN_MS
    }
}
