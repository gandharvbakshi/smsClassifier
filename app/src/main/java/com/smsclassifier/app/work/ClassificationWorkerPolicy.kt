package com.smsclassifier.app.work

import com.smsclassifier.app.classification.Prediction
import com.smsclassifier.app.data.MessageEntity

object ClassificationWorkerPolicy {
    const val OFFLINE_FALLBACK_REASON =
        "Cloud check skipped because the phone was offline; using basic on-device classification."
    const val SERVER_FALLBACK_REASON =
        "Cloud check unavailable; using basic on-device classification."

    fun hasUsableServerResult(prediction: Prediction): Boolean {
        return prediction.isOtp != null || prediction.isPhishing != null
    }

    fun fallbackPrediction(heuristicPrediction: Prediction, reason: String): Prediction {
        return heuristicPrediction.copy(
            reasons = (heuristicPrediction.reasons + reason).distinct()
        )
    }

    fun updatedMessage(
        message: MessageEntity,
        prediction: Prediction,
        usedServerResult: Boolean
    ): MessageEntity {
        return message.copy(
            isOtp = prediction.isOtp,
            otpIntent = if (usedServerResult) prediction.otpIntent else null,
            isPhishing = if (usedServerResult) prediction.isPhishing else null,
            phishScore = if (usedServerResult) prediction.phishScore else null,
            reasonsJson = reasonsJson(prediction.reasons),
            reviewed = true
        )
    }

    fun failedMessage(message: MessageEntity, errorMessage: String): MessageEntity {
        return message.copy(
            isOtp = false,
            otpIntent = null,
            isPhishing = null,
            phishScore = null,
            reasonsJson = reasonsJson(listOf("Classification error: ${errorMessage.take(80)}")),
            reviewed = true
        )
    }

    fun reasonsJson(reasons: List<String>): String? {
        val cleanReasons = reasons.filter { it.isNotBlank() }
        if (cleanReasons.isEmpty()) return null
        return cleanReasons.joinToString(prefix = "[", postfix = "]", separator = ",") { reason ->
            "\"${reason.escapeJsonString()}\""
        }
    }

    private fun String.escapeJsonString(): String {
        return buildString(length) {
            this@escapeJsonString.forEach { char ->
                when (char) {
                    '\\' -> append("\\\\")
                    '"' -> append("\\\"")
                    '\n' -> append("\\n")
                    '\r' -> append("\\r")
                    '\t' -> append("\\t")
                    else -> append(char)
                }
            }
        }
    }
}
