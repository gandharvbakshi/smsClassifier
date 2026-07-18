package com.smsclassifier.app.entitlement

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class TrialNudgePolicyTest {

    @Test
    fun selects_tightest_due_milestone_for_each_day_remaining() {
        assertNull(policy(6))
        assertEquals(TrialNudgeMilestone.DAY_5, policy(5))
        assertEquals(TrialNudgeMilestone.DAY_5, policy(4))
        assertEquals(TrialNudgeMilestone.DAY_3, policy(3))
        assertEquals(TrialNudgeMilestone.DAY_3, policy(2))
        assertEquals(TrialNudgeMilestone.DAY_1, policy(1))
        assertNull(policy(0))
    }

    @Test
    fun shown_combinations_skip_lapsed_higher_milestones_without_backlog() {
        assertEquals(
            TrialNudgeMilestone.DAY_3,
            policy(2, setOf(TrialNudgeMilestone.DAY_5))
        )
        assertEquals(
            TrialNudgeMilestone.DAY_1,
            policy(1, setOf(TrialNudgeMilestone.DAY_5, TrialNudgeMilestone.DAY_3))
        )
        assertNull(
            policy(
                4,
                setOf(TrialNudgeMilestone.DAY_5)
            )
        )
        assertNull(
            policy(
                2,
                setOf(TrialNudgeMilestone.DAY_3)
            )
        )
        assertNull(
            policy(
                1,
                setOf(
                    TrialNudgeMilestone.DAY_5,
                    TrialNudgeMilestone.DAY_3,
                    TrialNudgeMilestone.DAY_1
                )
            )
        )
    }

    @Test
    fun late_open_only_surfaces_the_tightest_remaining_due_milestone() {
        assertEquals(
            TrialNudgeMilestone.DAY_3,
            policy(2, setOf(TrialNudgeMilestone.DAY_5))
        )
        assertEquals(
            TrialNudgeMilestone.DAY_1,
            policy(1, setOf(TrialNudgeMilestone.DAY_5, TrialNudgeMilestone.DAY_3))
        )
    }

    @Test
    fun invalid_milestone_values_are_ignored() {
        assertEquals(TrialNudgeMilestone.DAY_5, TrialNudgeMilestone.fromDaysRemaining(5))
        assertNull(TrialNudgeMilestone.fromDaysRemaining(4))
        assertNull(TrialNudgeMilestone.fromDaysRemaining(2))
        assertNull(TrialNudgeMilestone.fromDaysRemaining(0))
        assertNull(TrialNudgeMilestone.fromDaysRemaining(-1))
    }

    @Test
    fun higher_milestones_are_marked_lapsed_when_a_lower_milestone_is_shown() {
        assertEquals(
            setOf(TrialNudgeMilestone.DAY_5),
            TrialNudgePolicy.lapsedHigherMilestones(TrialNudgeMilestone.DAY_3)
        )
        assertEquals(
            setOf(TrialNudgeMilestone.DAY_5, TrialNudgeMilestone.DAY_3),
            TrialNudgePolicy.lapsedHigherMilestones(TrialNudgeMilestone.DAY_1)
        )
        assertEquals(
            emptySet<TrialNudgeMilestone>(),
            TrialNudgePolicy.lapsedHigherMilestones(TrialNudgeMilestone.DAY_5)
        )
    }

    private fun policy(
        daysRemaining: Int,
        shown: Set<TrialNudgeMilestone> = emptySet()
    ): TrialNudgeMilestone? =
        TrialNudgePolicy.trialNudgeMilestone(daysRemaining, shown)
}
