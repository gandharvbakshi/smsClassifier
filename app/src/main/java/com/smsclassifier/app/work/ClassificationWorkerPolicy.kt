package com.smsclassifier.app.work

import com.smsclassifier.app.classification.Prediction
import com.smsclassifier.app.data.MessageEntity
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

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

    fun mergeServerWithHeuristic(
        serverPrediction: Prediction,
        heuristicPrediction: Prediction
    ): Prediction {
        val resolvedIsOtp = serverPrediction.isOtp ?: heuristicPrediction.isOtp
        val resolvedIntent = when {
            resolvedIsOtp != true -> null
            !serverPrediction.otpIntent.isNullOrBlank() -> serverPrediction.otpIntent
            else -> heuristicPrediction.otpIntent ?: "GENERIC_APP_ACTION_OTP"
        }
        return serverPrediction.copy(
            isOtp = resolvedIsOtp,
            otpIntent = resolvedIntent
        )
    }

    fun updatedMessage(
        message: MessageEntity,
        prediction: Prediction,
        usedServerResult: Boolean
    ): MessageEntity {
        val resolvedIsOtp = if (!usedServerResult && message.isOtp == true) {
            true
        } else {
            prediction.isOtp
        }
        return message.copy(
            isOtp = resolvedIsOtp,
            otpIntent = if (resolvedIsOtp == true) {
                prediction.otpIntent ?: message.otpIntent ?: "GENERIC_APP_ACTION_OTP"
            } else {
                null
            },
            // An on-device fallback can add OTP purpose, but it must never erase
            // a cloud risk result already stored on an older message.
            isPhishing = if (usedServerResult) prediction.isPhishing else message.isPhishing,
            phishScore = if (usedServerResult) prediction.phishScore else message.phishScore,
            reasonsJson = reasonsJson(prediction.reasons),
            linkVerdictsJson = if (usedServerResult) {
                Json.encodeToString(prediction.linkVerdicts)
            } else {
                message.linkVerdictsJson ?: Json.encodeToString(prediction.linkVerdicts)
            },
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
            linkVerdictsJson = "[]",
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
