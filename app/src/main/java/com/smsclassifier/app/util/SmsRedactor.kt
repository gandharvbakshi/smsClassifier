package com.smsclassifier.app.util

import kotlin.math.abs

/**
 * Deterministic redaction for ML uploads: same device + same SMS yields the same tokens.
 */
object SmsRedactor {

    private val digitRun = Regex("\\d{4,}")
    private val email = Regex("(?i)\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}\\b")

    const val TRAINING_REDACTION_SCHEME = "training_redaction_v3"

    fun redactForTraining(body: String, salt: String): String =
        replaceDigitRuns(
            email.replace(
                redactLinks(body, salt)
            ) { "<EMAIL:${stableAlphaToken(it.value, salt, 8)}>" },
            salt
        )

    private fun redactLinks(body: String, salt: String): String {
        val redacted = StringBuilder(body)
        MessageLinkParser.findLinks(body).asReversed().forEach { link ->
            val raw = body.substring(link.start, link.endExclusive)
            redacted.replace(
                link.start,
                link.endExclusive,
                "<URL:${stableAlphaToken(raw, salt, 8)}>"
            )
        }
        return redacted.toString()
    }

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
            "<DIGITS:$len:d${stableToken(raw, salt, 7)}>"
        }

    private fun stableToken(raw: String, salt: String, length: Int): String {
        val seed = abs((salt.hashCode().toLong() * 37L + raw.hashCode().toLong()).toInt())
        return seed.toString(36).padStart(length, '0').takeLast(length)
    }

    private fun stableAlphaToken(raw: String, salt: String, length: Int): String =
        stableToken(raw, salt, length).map { char ->
            if (char.isDigit()) ('k'.code + char.digitToInt()).toChar() else char
        }.joinToString("")
}
