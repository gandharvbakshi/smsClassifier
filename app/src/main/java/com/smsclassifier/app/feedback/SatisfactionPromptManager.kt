package com.smsclassifier.app.feedback

import android.content.Context
import com.smsclassifier.app.AppContainer

enum class SatisfactionPromptKind { D1, D5 }

/**
 * Phase 6 — lightweight satisfaction scheduling (SharedPreferences).
 */
class SatisfactionPromptManager(private val context: Context) {

    private val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun peekNextPrompt(now: Long = System.currentTimeMillis()): SatisfactionPromptKind? {
        if (!AppContainer.consentManager.onboardingSeenNow()) return null
        val firstOpen = context.getSharedPreferences("telemetry_launch", Context.MODE_PRIVATE)
            .getLong("first_open_at_ms", now)
        val dayMs = 86_400_000L
        val lastClosed = prefs.getLong(KEY_LAST_SESSION_DISMISS, 0L)
        if (lastClosed > 0L && now - lastClosed < MIN_PROMPT_GAP_MS) return null

        if (!prefs.getBoolean(KEY_D1_DONE, false)) {
            if (now - firstOpen >= dayMs) return SatisfactionPromptKind.D1
            return null
        }
        if (!prefs.getBoolean(KEY_D5_DONE, false)) {
            if (now - firstOpen >= 5 * dayMs) return SatisfactionPromptKind.D5
            return null
        }
        return null
    }

    fun markPromptFinished(kind: SatisfactionPromptKind) {
        prefs.edit().apply {
            when (kind) {
                SatisfactionPromptKind.D1 -> putBoolean(KEY_D1_DONE, true)
                SatisfactionPromptKind.D5 -> putBoolean(KEY_D5_DONE, true)
            }
        }.apply()
    }

    fun markDismissedSession() {
        prefs.edit().putLong(KEY_LAST_SESSION_DISMISS, System.currentTimeMillis()).apply()
    }

    companion object {
        private const val PREFS_NAME = "satisfaction_prefs"
        private const val KEY_D1_DONE = "d1_done"
        private const val KEY_D5_DONE = "d5_done"
        private const val KEY_LAST_SESSION_DISMISS = "last_session_dismiss"
        private const val MIN_PROMPT_GAP_MS = 3L * 86_400_000L
    }
}
