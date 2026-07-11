package com.smsclassifier.app.analytics

import java.time.Instant
import java.time.ZoneOffset
import java.time.temporal.ChronoUnit

object RetentionMilestonePolicy {
    private val offsetToEventName = linkedMapOf(
        1L to "retention_d1",
        3L to "retention_d3",
        7L to "retention_d7",
    )

    fun seedFirstObservedLaunchAt(
        existingFirstObservedLaunchAtMs: Long?,
        telemetryLaunchFirstOpenAtMs: Long?,
        nowMs: Long,
    ): Long = existingFirstObservedLaunchAtMs ?: telemetryLaunchFirstOpenAtMs ?: nowMs

    fun dueEventName(
        firstObservedLaunchAtMs: Long,
        nowMs: Long,
        alreadyLogged: Set<String> = emptySet(),
    ): String? {
        if (nowMs < firstObservedLaunchAtMs) return null

        val launchUtcDay = utcDay(firstObservedLaunchAtMs)
        val nowUtcDay = utcDay(nowMs)
        val offsetDays = ChronoUnit.DAYS.between(launchUtcDay, nowUtcDay)
        val eventName = offsetToEventName[offsetDays] ?: return null
        return if (eventName in alreadyLogged) null else eventName
    }

    private fun utcDay(epochMs: Long) = Instant.ofEpochMilli(epochMs).atZone(ZoneOffset.UTC).toLocalDate()
}
