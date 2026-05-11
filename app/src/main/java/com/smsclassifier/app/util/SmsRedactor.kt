package com.smsclassifier.app.util

import kotlin.math.abs

/**
 * Deterministic redaction for ML uploads: same device + same SMS → same fake digits.
 */
object SmsRedactor {

    private val digitRun = Regex("\\d{4,}")

    fun redactForTraining(body: String, salt: String): String =
        digitRun.replace(body) { m ->
            val raw = m.value
            val len = raw.length.coerceAtMost(32)
            val seed = (salt.hashCode().toLong() * 31L + raw.hashCode().toLong()).xor(len.toLong())
            buildString(len) {
                for (i in 0 until len) {
                    val d = kotlin.math.abs((seed shr (i * 3)).toInt() % 10)
                    append('0' + d)
                }
            }
        }
}
