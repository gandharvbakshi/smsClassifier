package com.smsclassifier.app.analytics

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.time.Instant

class RetentionMilestonePolicyTest {

    @Test
    fun fires_d1_d3_d7_only_on_exact_utc_day_offsets() {
        val launch = utc("2026-07-10T08:15:30Z")

        assertEquals("retention_d1", RetentionMilestonePolicy.dueEventName(launch, utc("2026-07-11T00:00:00Z")))
        assertEquals("retention_d3", RetentionMilestonePolicy.dueEventName(launch, utc("2026-07-13T23:59:59Z")))
        assertEquals("retention_d7", RetentionMilestonePolicy.dueEventName(launch, utc("2026-07-17T12:00:00Z")))
    }

    @Test
    fun does_not_fire_on_non_milestone_days() {
        val launch = utc("2026-07-10T08:15:30Z")

        assertNull(RetentionMilestonePolicy.dueEventName(launch, utc("2026-07-10T23:59:59Z")))
        assertNull(RetentionMilestonePolicy.dueEventName(launch, utc("2026-07-12T00:00:00Z")))
        assertNull(RetentionMilestonePolicy.dueEventName(launch, utc("2026-07-14T23:59:59Z")))
    }

    @Test
    fun missed_day_does_not_backfill_later() {
        val launch = utc("2026-07-10T08:15:30Z")

        assertNull(RetentionMilestonePolicy.dueEventName(launch, utc("2026-07-12T10:00:00Z")))
        assertEquals("retention_d3", RetentionMilestonePolicy.dueEventName(launch, utc("2026-07-13T10:00:00Z")))
    }

    @Test
    fun already_logged_milestone_is_suppressed_but_later_one_can_still_fire() {
        val launch = utc("2026-07-10T08:15:30Z")
        val alreadyLogged = setOf("retention_d1")

        assertNull(
            RetentionMilestonePolicy.dueEventName(
                firstObservedLaunchAtMs = launch,
                nowMs = utc("2026-07-11T10:00:00Z"),
                alreadyLogged = alreadyLogged,
            )
        )
        assertEquals(
            "retention_d3",
            RetentionMilestonePolicy.dueEventName(
                firstObservedLaunchAtMs = launch,
                nowMs = utc("2026-07-13T10:00:00Z"),
                alreadyLogged = alreadyLogged,
            )
        )
    }

    @Test
    fun uses_exact_utc_calendar_day_boundaries() {
        val launch = utc("2026-07-10T23:59:30Z")

        assertEquals("retention_d1", RetentionMilestonePolicy.dueEventName(launch, utc("2026-07-11T00:00:00Z")))
        assertNull(RetentionMilestonePolicy.dueEventName(launch, utc("2026-07-10T23:59:59Z")))
    }

    @Test
    fun negative_clock_skew_does_not_fire() {
        val launch = utc("2026-07-10T08:15:30Z")
        assertNull(RetentionMilestonePolicy.dueEventName(launch, utc("2026-07-10T08:15:29Z")))
        assertNull(RetentionMilestonePolicy.dueEventName(launch, utc("2026-07-09T23:59:59Z")))
    }

    @Test
    fun seed_first_observed_launch_prefers_existing_retention_then_telemetry_launch_then_now() {
        val now = utc("2026-07-10T08:15:30Z")
        assertEquals(111L, RetentionMilestonePolicy.seedFirstObservedLaunchAt(111L, 222L, now))
        assertEquals(222L, RetentionMilestonePolicy.seedFirstObservedLaunchAt(null, 222L, now))
        assertEquals(now, RetentionMilestonePolicy.seedFirstObservedLaunchAt(null, null, now))
    }

    private fun utc(isoInstant: String): Long =
        Instant.parse(isoInstant).toEpochMilli()
}
