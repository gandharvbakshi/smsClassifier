package com.smsclassifier.app.util

import kotlin.math.abs

/**
 * Deterministic redaction for ML uploads: same device + same SMS yields the same tokens.
 */
object SmsRedactor {

    private val digitRun = Regex("\\d{4,}")
    private val url = Regex("(?i)\\b(?:https?://|www\\.)\\S+")
    private val email = Regex("(?i)\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}\\b")

    const val TRAINING_REDACTION_SCHEME = "training_redaction_v2"

    fun redactForTraining(body: String, salt: String): String =
        replaceDigitRuns(
            email.replace(
                url.replace(body) { "<URL:${stableToken(it.value, salt, 8)}>" }
            ) { "<EMAIL:${stableToken(it.value, salt, 8)}>" },
            salt
        )

    fun redactSenderForTraining(sender: String, salt: String): String {
        val trimmed = sender.trim()
        if (trimmed.isEmpty()) return trimmed
        if (trimmed.any { it.isLetter() }) return trimmed.take(20)
        return "<SENDER:${stableToken(trimmed, salt, 8)}>"
    }

    private fun replaceDigitRuns(text: String, salt: String): String =
        digitRun.replace(text) { m ->
            val raw = m.value
            val len = raw.length.coerceAtMost(32)
            val seed = (salt.hashCode().toLong() * 31L + raw.hashCode().toLong()).xor(len.toLong())
            buildString(len) {
                for (i in 0 until len) {
                    val d = abs((seed shr (i * 3)).toInt() % 10)
                    append('0' + d)
                }
            }
        }

    private fun stableToken(raw: String, salt: String, length: Int): String {
        val seed = abs((salt.hashCode().toLong() * 37L + raw.hashCode().toLong()).toInt())
        return seed.toString(36).padStart(length, '0').takeLast(length)
    }
}
