package com.smsclassifier.app.util

import com.smsclassifier.app.data.MessageEntity

object ReplyPolicy {
    private val phoneFormat = Regex("""\+?[0-9(][0-9(). \-]*[0-9)]""")

    /**
     * Accept ordinary phone numbers with common display formatting. Leave short
     * codes unavailable because sender text alone cannot establish reply support.
     */
    fun recipient(sender: String): String? {
        val address = sender.trim()
        if (!phoneFormat.matches(address)) return null

        val digits = ThreadUtils.normalizePhoneNumber(address)
        val international = address.startsWith('+')
        val minimumLength = if (international) 8 else 7
        if (digits.length !in minimumLength..15) return null
        if (international && digits.startsWith('0')) return null
        return if (international) "+$digits" else digits
    }

    fun requiresConfirmation(message: MessageEntity): Boolean =
        ClassificationUtils.detailRiskLevel(message) != ClassificationUtils.RiskLevel.LOW

    /**
     * Eligible phone senders open the composer. Flagged or suspicious messages
     * stay on the detail screen until the user confirms. Other senders cannot reply.
     */
    fun route(message: MessageEntity): Route? {
        if (recipient(message.sender) == null) return null
        return if (requiresConfirmation(message)) Route.CONFIRM else Route.COMPOSER
    }

    enum class Route { COMPOSER, CONFIRM }

    const val UNAVAILABLE_MESSAGE = "Replies are unavailable for this sender."
}
