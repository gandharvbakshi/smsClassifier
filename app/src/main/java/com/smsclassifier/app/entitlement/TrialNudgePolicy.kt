package com.smsclassifier.app.entitlement

enum class TrialNudgeMilestone(val daysRemaining: Int) {
    DAY_5(5),
    DAY_3(3),
    DAY_1(1);

    companion object {
        fun fromDaysRemaining(daysRemaining: Int): TrialNudgeMilestone? =
            values().firstOrNull { it.daysRemaining == daysRemaining }
    }
}

object TrialNudgePolicy {

    private val milestonesAscending = TrialNudgeMilestone.values()
        .sortedBy { it.daysRemaining }

    fun trialNudgeMilestone(
        daysRemaining: Int,
        shownMilestones: Set<TrialNudgeMilestone> = emptySet()
    ): TrialNudgeMilestone? {
        if (daysRemaining <= 0) return null
        val tightestDue = milestonesAscending.firstOrNull { daysRemaining <= it.daysRemaining }
            ?: return null
        return tightestDue.takeUnless { it in shownMilestones }
    }

    fun lapsedHigherMilestones(milestone: TrialNudgeMilestone): Set<TrialNudgeMilestone> =
        milestonesAscending.filter { it.daysRemaining > milestone.daysRemaining }.toSet()
}
