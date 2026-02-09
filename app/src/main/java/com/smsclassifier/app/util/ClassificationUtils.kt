package com.smsclassifier.app.util

import com.smsclassifier.app.classification.HeuristicOtpClassifier
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.ui.badges.BadgeType
import com.smsclassifier.app.ui.badges.SensitivityType

object ClassificationUtils {
    private val OTP_REGEX = Regex("\\b\\d{4,8}\\b")
    private const val OTP_COPY_MIN_CONFIDENCE = 0.8f

    fun riskBadgeType(message: MessageEntity): BadgeType {
        val phishScore = message.phishScore ?: 0f
        return when {
            message.isPhishing == true || phishScore >= 0.6f -> BadgeType.PHISHING
            phishScore in 0.3f..0.6f -> BadgeType.SUSPICIOUS
            message.isOtp == true && phishScore < 0.3f -> BadgeType.SAFE
            else -> BadgeType.SAFE
        }
    }

    fun sensitivityType(message: MessageEntity): SensitivityType {
        if (message.isOtp != true) return SensitivityType.NONE
        return when (message.otpIntent) {
            "BANK_OR_CARD_TXN_OTP",
            "FINANCIAL_LOGIN_OTP",
            "APP_ACCOUNT_CHANGE_OTP",
            "UPI_TXN_OR_PIN_OTP" -> SensitivityType.DO_NOT_SHARE
            "DELIVERY_OR_SERVICE_OTP" -> SensitivityType.COURIER_ONLY
            else -> SensitivityType.INFO
        }
    }

    fun extractOtpCode(body: String): String? {
        return OTP_REGEX.find(body)?.value
    }

    fun extractOtpForCopy(body: String, sender: String?, isOtp: Boolean?): String? {
        val code = extractOtpCode(body) ?: return null
        if (isOtp == true) return code

        val heuristic = HeuristicOtpClassifier.classify(body, sender)
        return if (heuristic.isOtp && heuristic.confidence >= OTP_COPY_MIN_CONFIDENCE) {
            code
        } else {
            null
        }
    }
}

