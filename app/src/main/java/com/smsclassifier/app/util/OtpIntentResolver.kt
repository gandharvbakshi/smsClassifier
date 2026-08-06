package com.smsclassifier.app.util

import com.smsclassifier.app.classification.HeuristicOtpClassifier
import com.smsclassifier.app.data.MessageEntity

enum class OtpSharingGuidance {
    NEVER_SHARE,
    COURIER_ONLY,
    NONE
}

data class OtpIntentPresentation(
    val label: String,
    val safetyMessage: String?,
    val sharingGuidance: OtpSharingGuidance
)

/**
 * One source of truth for the plain-language purpose and sharing guidance shown
 * anywhere an OTP appears. Stored classifier intent wins; the on-device
 * heuristic fills older or incomplete rows while the background backfill runs.
 */
object OtpIntentResolver {
    private const val NEVER_SHARE = "Never share this OTP"
    private const val COURIER_ONLY = "Share only with your courier"

    fun resolve(message: MessageEntity): OtpIntentPresentation {
        return resolve(
            otpIntent = message.otpIntent,
            sender = message.sender,
            body = message.body
        )
    }

    fun resolve(
        otpIntent: String?,
        sender: String? = null,
        body: String? = null
    ): OtpIntentPresentation {
        val storedIntent = otpIntent
            ?.takeIf { it.isNotBlank() && it != "NOT_OTP" }
        val inferredIntent = body?.takeIf { it.isNotBlank() }
            ?.let { HeuristicOtpClassifier.classify(it, sender).suggestedIntent }
        val resolvedIntent = if (
            storedIntent == null || storedIntent.equals("GENERIC_APP_ACTION_OTP", ignoreCase = true)
        ) {
            inferredIntent ?: storedIntent
        } else {
            storedIntent
        }
        val isWhatsApp = isWhatsAppContext(sender, body)

        return when (resolvedIntent?.uppercase()) {
            "BANK_OR_CARD_TXN_OTP" -> neverShare("Bank transaction OTP")
            "UPI_TXN_OR_PIN_OTP" -> neverShare("UPI payment OTP")
            "FINANCIAL_LOGIN_OTP" -> neverShare("Bank login OTP")
            "APP_ACCOUNT_CHANGE_OTP" -> neverShare(
                if (isWhatsApp) "WhatsApp account change OTP" else "Account change OTP"
            )
            "APP_LOGIN_OTP" -> neverShare(
                if (isWhatsApp) "WhatsApp login OTP" else "App login OTP"
            )
            "KYC_OR_ESIGN_OTP" -> neverShare("KYC or e-sign OTP")
            "DELIVERY_OR_SERVICE_OTP" -> OtpIntentPresentation(
                label = "Courier delivery OTP",
                safetyMessage = COURIER_ONLY,
                sharingGuidance = OtpSharingGuidance.COURIER_ONLY
            )
            else -> OtpIntentPresentation(
                label = "OTP",
                safetyMessage = null,
                sharingGuidance = OtpSharingGuidance.NONE
            )
        }
    }

    fun talkBackDescription(
        presentation: OtpIntentPresentation,
        senderName: String,
        code: String
    ): String {
        val spokenCode = code.filter(Char::isDigit).toCharArray().joinToString(" ")
        return buildList {
            add("${presentation.label} from ${senderName.ifBlank { "sender" }}.")
            add("$spokenCode.")
            presentation.safetyMessage?.let { add("$it.") }
            add("Double tap to copy OTP.")
        }.joinToString(" ")
    }

    private fun neverShare(label: String): OtpIntentPresentation {
        return OtpIntentPresentation(
            label = label,
            safetyMessage = NEVER_SHARE,
            sharingGuidance = OtpSharingGuidance.NEVER_SHARE
        )
    }

    private fun isWhatsAppContext(sender: String?, body: String?): Boolean {
        val senderUpper = sender.orEmpty().uppercase()
        return body.orEmpty().contains("whatsapp", ignoreCase = true) ||
            senderUpper.contains("WHATSAPP") ||
            Regex("(^|[-_])WA($|[-_])").containsMatchIn(senderUpper)
    }
}
