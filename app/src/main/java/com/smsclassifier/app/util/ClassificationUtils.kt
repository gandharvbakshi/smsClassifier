package com.smsclassifier.app.util

import com.smsclassifier.app.classification.HeuristicOtpClassifier
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.ui.badges.BadgeType
import com.smsclassifier.app.ui.badges.SensitivityType

object ClassificationUtils {
    private val OTP_REGEX = Regex("(?<!\\d)(?:\\d{4,8}|\\d{3}[\\s-]\\d{3})(?!\\d)")
    private const val OTP_COPY_MIN_CONFIDENCE = 0.8f
    private val URL_REGEX = Regex("https?://|www\\.|\\b[a-z0-9.-]+\\.[a-z]{2,}\\b", RegexOption.IGNORE_CASE)
    private val OTP_KEYWORD_REGEX = Regex(
        "\\b(otp|one time password|verification code|authentication code|login code|security code|code)\\b",
        RegexOption.IGNORE_CASE
    )
    private val AMOUNT_CONTEXT_REGEX = Regex(
        "(₹|\\brs\\.?\\b|\\binr\\b|\\busd\\b|\\bamount\\b|\\btxn of\\b|\\btransaction of\\b|\\bspent\\b|\\bdebited\\b|\\bcredited\\b)",
        RegexOption.IGNORE_CASE
    )

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
        if (message.userCorrected) return message.isOtp == true
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

    fun riskSummary(message: MessageEntity): String {
        return when (detailRiskLevel(message)) {
            RiskLevel.HIGH -> "High"
            RiskLevel.MEDIUM -> "Be careful"
            else -> "Very low"
        }
    }

    fun detailRiskLevel(message: MessageEntity): RiskLevel {
        val phishScore = message.phishScore ?: 0f
        return when {
            message.isPhishing == true || phishScore >= 0.6f -> RiskLevel.HIGH
            phishScore >= 0.3f -> RiskLevel.MEDIUM
            else -> RiskLevel.LOW
        }
    }

    fun isScamLikely(message: MessageEntity): Boolean = detailRiskLevel(message) == RiskLevel.HIGH

    fun humanizeIntent(intent: String?): String? {
        if (intent == null || intent == "NOT_OTP") return null
        return OtpIntentResolver.resolve(otpIntent = intent).label
    }

    /**
     * High-precision warning policy for OTP notifications.
     *
     * Delivery OTP / PIN messages should stay quiet, while explicit "do not
     * share" language or clear financial / UPI context should surface a
     * warning.
     */
    fun shouldWarnOnOtpNotification(
        body: String,
        sender: String?,
        otpIntent: String?
    ): Boolean {
        return OtpIntentResolver.resolve(otpIntent, sender, body).sharingGuidance ==
            OtpSharingGuidance.NEVER_SHARE
    }

    fun plainReasons(message: MessageEntity, rawReasons: List<String>): List<String> {
        val mapped = rawReasons.mapNotNull { plainReason(it) }
            .filter { isOtpEffective(message) || !it.isOtpReason() }
            .distinct()
            .take(4)
            .toMutableList()

        if (mapped.isEmpty()) {
            mapped.addAll(defaultPlainReasons(message))
        } else {
            val remainingSlots = (4 - mapped.size).coerceAtLeast(0)
            defaultPlainReasons(message)
                .filterNot { it in mapped }
                .take(remainingSlots)
                .forEach { mapped.add(it) }
        }

        return mapped.take(4)
    }

    fun plainReason(rawReason: String): String? {
        val text = rawReason.lowercase()
        return when {
            text.contains("numeric code") || text.contains("short code") ->
                "Contains a short OTP that expires soon"
            text.contains("heuristic otp") ||
                text.contains("otp wording") ||
                text.contains("otp pattern") ||
                text.contains("strong otp") ||
                text.contains("otp-style") ||
                text.contains("multiple otp") ->
                "Wording matches a login or payment OTP"
            text.contains("known bank sender") ||
                text.contains("registered") ||
                text.contains("recognised sender") ||
                text.contains("sender id") ->
                "Sent from a registered sender ID"
            text.contains("no url") ->
                "No links asking you to act"
            text.contains("shortened url") ||
                text.contains("bit.ly") ||
                text.contains("tinyurl") ||
                text.contains("hidden link") ->
                "Hidden link - you cannot see where it goes"
            text.contains("urgency") ||
                text.contains("deadline") ||
                text.contains("midnight") ->
                "Pushes you to act before a deadline"
            text.contains("prize") ||
                text.contains("lottery") ||
                text.contains("won") ->
                "Promises a large prize for no reason"
            text.contains("transaction/marketing context") ||
                text.contains("transaction") ||
                text.contains("marketing") ->
                "Reads like a normal transaction alert"
            text.contains("insufficient otp context") ->
                "Does not look like an OTP request"
            text.contains("error") ||
                text.contains("failed") ||
                text.contains("unable") ||
                text.contains("timeout") ->
                null
            else -> null
        }
    }

    private fun defaultPlainReasons(message: MessageEntity): List<String> {
        val body = message.body.lowercase()
        return when {
            isScamLikely(message) -> buildList {
                if (body.contains("bit.ly") || body.contains("tinyurl")) {
                    add("Hidden link - you cannot see where it goes")
                } else if (URL_REGEX.containsMatchIn(message.body)) {
                    add("Includes a link asking you to act")
                }
                if (Regex("\\b(won|prize|lottery|reward)\\b").containsMatchIn(body)) {
                    add("Promises a large prize for no reason")
                }
                if (Regex("\\b(urgent|deadline|limited|midnight|expire|blocked)\\b").containsMatchIn(body)) {
                    add("Pushes you to act before a deadline")
                }
                if (isEmpty()) add("Wording is unusual for a trusted sender")
            }
            isOtpEffective(message) -> buildList {
                add("Contains a short OTP that expires soon")
                if (humanizeIntent(message.otpIntent) != null) {
                    add("Wording matches a login or payment OTP")
                }
                add("Sender ID matches the message context")
            }
            else -> buildList {
                add("Reads like a normal transaction alert")
                if (!URL_REGEX.containsMatchIn(message.body)) {
                    add("No links asking you to act")
                }
                add("Does not look like an OTP request")
            }
        }
    }

    private fun String.isOtpReason(): Boolean {
        return this == "Contains a short OTP that expires soon" ||
            this == "Wording matches a login or payment OTP"
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
        return when (OtpIntentResolver.resolve(message).sharingGuidance) {
            OtpSharingGuidance.NEVER_SHARE -> SensitivityType.DO_NOT_SHARE
            OtpSharingGuidance.COURIER_ONLY -> SensitivityType.COURIER_ONLY
            OtpSharingGuidance.NONE -> SensitivityType.NONE
        }
    }

    fun extractOtpCode(body: String): String? {
        val matches = OTP_REGEX.findAll(body).toList()
        if (matches.isEmpty()) return null
        return matches
            .map { match ->
                OtpCandidate(
                    code = match.value.filter(Char::isDigit),
                    score = scoreOtpCandidate(body, match)
                )
            }
            .maxByOrNull { it.score }
            ?.code
    }

    private fun scoreOtpCandidate(body: String, match: MatchResult): Int {
        val code = match.value.filter(Char::isDigit)
        val start = match.range.first
        val end = match.range.last + 1
        val before = body.substring(maxOf(0, start - 80), start)
        val after = body.substring(end, minOf(body.length, end + 80))
        val nearby = before + " " + after

        var score = when (code.length) {
            6 -> 30
            5 -> 18
            4 -> 10
            else -> 14
        }
        if (OTP_KEYWORD_REGEX.containsMatchIn(before)) score += 14
        if (OTP_KEYWORD_REGEX.containsMatchIn(after)) score += 8
        if (Regex("\\bis\\s*$", RegexOption.IGNORE_CASE).containsMatchIn(before.takeLast(10))) {
            score += 10
        }
        if (Regex("\\b(do not share|valid for|expires?|use|enter)\\b", RegexOption.IGNORE_CASE).containsMatchIn(after)) {
            score += 10
        }
        if (AMOUNT_CONTEXT_REGEX.containsMatchIn(before.takeLast(28))) score -= 24
        if (Regex("\\b(at|on)\\s+[A-Z0-9]", RegexOption.IGNORE_CASE).containsMatchIn(after.take(24))) {
            score -= 8
        }
        if (!OTP_KEYWORD_REGEX.containsMatchIn(nearby)) score -= 10

        return score
    }

    private data class OtpCandidate(val code: String, val score: Int)

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

    fun extractOtpForCopy(message: MessageEntity): String? {
        val code = extractOtpCode(message.body) ?: return null
        if (message.userCorrected) return if (message.isOtp == true) code else null
        return extractOtpForCopy(message.body, message.sender, message.isOtp)
    }

    fun applyUserCorrection(
        message: MessageEntity,
        correctionKind: String,
        correctedOtpIntent: String? = null
    ): MessageEntity {
        return when (correctionKind) {
            "actually_otp" -> message.copy(
                isOtp = true,
                otpIntent = message.otpIntent?.takeUnless { it == "NOT_OTP" }
                    ?: "GENERIC_APP_ACTION_OTP",
                reasonsJson = null,
                reviewed = true,
                userCorrected = true
            )
            "other" -> if (correctedOtpIntent != null) {
                message.copy(
                    isOtp = true,
                    otpIntent = correctedOtpIntent,
                    reasonsJson = null,
                    reviewed = true,
                    userCorrected = true
                )
            } else {
                message.copy(reasonsJson = null, reviewed = true, userCorrected = true)
            }
            "not_otp" -> message.copy(
                isOtp = false,
                otpIntent = null,
                reasonsJson = null,
                reviewed = true,
                userCorrected = true
            )
            "phishing" -> message.copy(
                isPhishing = true,
                phishScore = maxOf(message.phishScore ?: 0f, 0.8f),
                reasonsJson = null,
                reviewed = true,
                userCorrected = true
            )
            "not_phishing" -> message.copy(
                isPhishing = false,
                phishScore = 0f,
                reasonsJson = null,
                reviewed = true,
                userCorrected = true
            )
            else -> message.copy(reasonsJson = null, reviewed = true, userCorrected = true)
        }
    }
}
