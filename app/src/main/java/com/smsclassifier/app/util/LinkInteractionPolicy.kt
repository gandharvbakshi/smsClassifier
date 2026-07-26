package com.smsclassifier.app.util

import com.smsclassifier.app.classification.LinkVerdict
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.Json

object LinkInteractionPolicy {
    fun isAllowed(
        scamLikely: Boolean,
        linkVerdictsJson: String?,
        messageBody: String
    ): Boolean {
        if (scamLikely) return false
        // Messages classified before link verdict persistence retain the
        // behavior users already had. New classifications always store JSON.
        if (linkVerdictsJson == null) return true
        val verdicts = runCatching {
            Json.decodeFromString<List<LinkVerdict>>(linkVerdictsJson)
        }.getOrElse { return false }
        val detectedUrls = MessageLinkParser.findLinks(messageBody)
            .map { it.url }
            .toSet()
        val checkedUrls = verdicts.map { it.url }.toSet()
        return detectedUrls.isNotEmpty() &&
            detectedUrls == checkedUrls &&
            verdicts.all { it.status == "NO_MATCH" }
    }
}
