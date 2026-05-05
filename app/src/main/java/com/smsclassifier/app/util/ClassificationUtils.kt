package com.smsclassifier.app.util

import com.smsclassifier.app.classification.HeuristicOtpClassifier
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.ui.badges.BadgeType
import com.smsclassifier.app.ui.badges.SensitivityType

object ClassificationUtils {
    private val OTP_REGEX = Regex("\\b\\d{4,8}\\b")
    private const val OTP_COPY_MIN_CONFIDENCE = 0.8f

    /**
     * True if the heuristic classifier is *certain* this is NOT an OTP — i.e.
     * it found transaction/marketing/delivery context AND no strong OTP keyword.
     * Used to override the server-side ML model when it has clearly mistaken
     * a transaction notification ("debited Rs 150 ... call 18002662") for an OTP.
     */
    fun isHeuristicVeto(body: String, sender: String?): Boolean {
        val r = HeuristicOtpClassifier.classify(body, sender)
        return !r.isOtp && r.reasons.any {
            it.contains("Transaction/marketing context", ignoreCase = true)
        }
    }

    fun isOtpEffective(message: MessageEntity): Boolean {
        if (message.isOtp != true) return false
        // Even if the model says yes, trust an explicit heuristic veto.
        if (isHeuristicVeto(message.body, message.sender)) return false
        return true
    }

    fun riskBadgeType(message: MessageEntity): BadgeType {
        val phishScore = message.phishScore ?: 0f
        return when {
            message.isPhishing == true || phishScore >= 0.6f -> BadgeType.PHISHING
            phishScore in 0.3f..0.6f -> BadgeType.SUSPICIOUS
            isOtpEffective(message) && phishScore < 0.3f -> BadgeType.SAFE
            else -> BadgeType.SAFE
        }
    }

    enum class RiskLevel { NONE, LOW, MEDIUM, HIGH }

    fun riskLevelForThread(latest: MessageEntity?): RiskLevel = when {
        latest == null -> RiskLevel.NONE
        latest.isPhishing == true -> RiskLevel.HIGH
        (latest.phishScore ?: 0f) >= 0.5f -> RiskLevel.MEDIUM
        (latest.phishScore ?: 0f) >= 0.3f -> RiskLevel.LOW
        else -> RiskLevel.NONE
    }

    fun sensitivityType(message: MessageEntity): SensitivityType {
        if (!isOtpEffective(message)) return SensitivityType.NONE
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

    /**
     * Resolve the OTP code only when the message is **really** an OTP. Strict:
     *
     *  1. There must be a 4-8 digit numeric code in the body.
     *  2. The heuristic must explicitly classify it as an OTP with high
     *     confidence, OR the server-ML said yes AND the heuristic does not
     *     veto it (transaction / marketing context).
     *
     * Previously we trusted `isOtp == true` blindly, which surfaced "OTP" badges
     * on bank debit/credit notifications like "Acct XX696 debited for Rs 150 ...
     * call 18002662" — exactly the false positives the user reported.
     */
    fun extractOtpForCopy(body: String, sender: String?, isOtp: Boolean?): String? {
        val code = extractOtpCode(body) ?: return null
        val heuristic = HeuristicOtpClassifier.classify(body, sender)

        // Hard veto: heuristic confidently rejected this as a transaction /
        // marketing / delivery message. Don't trust ML over our rule.
        val vetoed = !heuristic.isOtp && heuristic.reasons.any {
            it.contains("Transaction/marketing context", ignoreCase = true)
        }
        if (vetoed) return null

        if (heuristic.isOtp && heuristic.confidence >= OTP_COPY_MIN_CONFIDENCE) return code
        if (isOtp == true && heuristic.isOtp) return code
        if (isOtp == true && heuristic.confidence >= 0.6f) return code

        return null
    }
}
