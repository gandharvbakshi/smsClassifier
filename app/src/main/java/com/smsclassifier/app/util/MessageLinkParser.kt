package com.smsclassifier.app.util

import java.net.IDN

/**
 * Extracts conservative plain-text links from SMS bodies.
 *
 * Recognized inputs:
 * - literal http:// and https:// URLs
 * - literal www. URLs
 * - scheme-less bare domains with optional paths/query/fragment
 *
 * Bare www and domain-style links are normalized to https:// in the returned
 * URL while start/end still point to the original display text.
 */
object MessageLinkParser {

    data class LinkMatch(
        val url: String,
        val start: Int,
        val endExclusive: Int
    )

    private val trailingPunctuation = setOf(
        '.', ',', '!', '?', ':', ';',
        ')', ']', '}', '>', '"', '\''
    )

    private val blockedBoundaryChars = setOf(
        '.', '-', '_', '/', '@', ':'
    )

    fun findLinks(text: String): List<LinkMatch> {
        if (text.isEmpty()) return emptyList()

        val matches = ArrayList<LinkMatch>()
        var index = 0
        while (index < text.length) {
            val match = findMatchAt(text, index)
            if (match != null) {
                matches += match
                index = match.endExclusive
            } else {
                index++
            }
        }
        return matches
    }

    private fun findMatchAt(text: String, index: Int): LinkMatch? {
        val httpScheme = when {
            text.regionMatches(index, "https://", 0, "https://".length, ignoreCase = true) -> "https://"
            text.regionMatches(index, "http://", 0, "http://".length, ignoreCase = true) -> "http://"
            else -> null
        }
        if (httpScheme != null) {
            if (!hasAcceptableSchemeBoundary(text, index)) return null
            val end = trimTokenEnd(text, index)
            return parseHttpUrl(text, index, end)
        }

        if (text.regionMatches(index, "www.", 0, 4, ignoreCase = true)) {
            if (!hasAcceptableBoundary(text, index)) return null
            val end = trimTokenEnd(text, index)
            return parseDomainUrl(text, index, end, stripWwwPrefix = true)
        }

        if (!isBareDomainStart(text, index)) return null

        val end = trimTokenEnd(text, index)
        return parseDomainUrl(text, index, end, stripWwwPrefix = false)
    }

    private fun hasAcceptableBoundary(text: String, start: Int): Boolean {
        if (start <= 0) return true
        val previous = text[start - 1]
        return !previous.isLetterOrDigit() && previous !in blockedBoundaryChars
    }

    private fun hasAcceptableSchemeBoundary(text: String, start: Int): Boolean {
        if (start <= 0) return true
        return !text[start - 1].isLetterOrDigit()
    }

    private fun isBareDomainStart(text: String, start: Int): Boolean {
        if (!hasAcceptableBoundary(text, start)) return false
        val c = text[start]
        return c.isLetterOrDigit()
    }

    private fun trimTokenEnd(text: String, start: Int): Int {
        var end = start
        while (end < text.length && !text[end].isWhitespace()) {
            end++
        }

        while (end > start && text[end - 1] in trailingPunctuation) {
            end--
        }
        return end
    }

    private fun parseHttpUrl(text: String, start: Int, end: Int): LinkMatch? {
        if (end <= start) return null
        val raw = text.substring(start, end)

        val schemeSeparator = raw.indexOf("://")
        if (schemeSeparator <= 0) return null

        val scheme = raw.substring(0, schemeSeparator)
        if (!scheme.equals("http", ignoreCase = true) && !scheme.equals("https", ignoreCase = true)) {
            return null
        }

        val remainder = raw.substring(schemeSeparator + 3)
        val authorityEnd = remainder.indexOfAny(charArrayOf('/', '?', '#')).let { if (it == -1) remainder.length else it }
        val authority = remainder.substring(0, authorityEnd)
        val normalizedAuthority = normalizeAuthority(authority) ?: return null
        if (normalizedAuthority.isEmpty()) return null
        val suffix = remainder.substring(authorityEnd).substringBefore('#')

        return LinkMatch(
            url = "${scheme.lowercase()}://$normalizedAuthority$suffix",
            start = start,
            endExclusive = end
        )
    }

    private fun parseDomainUrl(text: String, start: Int, end: Int, stripWwwPrefix: Boolean): LinkMatch? {
        if (end <= start) return null
        val raw = text.substring(start, end)

        val authorityAndSuffix = if (stripWwwPrefix) {
            if (!raw.regionMatches(0, "www.", 0, 4, ignoreCase = true)) return null
            raw.substring(4)
        } else raw
        if (authorityAndSuffix.isEmpty()) return null

        val authorityEnd = authorityAndSuffix.indexOfAny(charArrayOf('/', '?', '#')).let { if (it == -1) authorityAndSuffix.length else it }
        val authority = authorityAndSuffix.substring(0, authorityEnd)

        val normalizedAuthority = normalizeAuthority(authority) ?: return null
        if (normalizedAuthority.isEmpty()) return null
        val suffix = authorityAndSuffix.substring(authorityEnd).substringBefore('#')
        val canonicalAuthority = if (stripWwwPrefix) {
            "www.$normalizedAuthority"
        } else {
            normalizedAuthority
        }

        return LinkMatch(
            url = "https://$canonicalAuthority$suffix",
            start = start,
            endExclusive = end
        )
    }

    private fun normalizeAuthority(authority: String): String? {
        if (authority.isEmpty()) return null
        if (authority.contains('@') || authority.contains('[') || authority.contains(']')) return null
        if (authority.contains(' ') || authority.contains('\\')) return null

        val hostPort = splitHostAndPort(authority) ?: return null
        val host = normalizeDomainHost(hostPort.first) ?: return null

        return hostPort.second?.let { "$host:$it" } ?: host
    }

    private fun splitHostAndPort(authority: String): Pair<String, String?>? {
        val colonIndex = authority.lastIndexOf(':')
        if (colonIndex <= 0) return authority to null

        val host = authority.substring(0, colonIndex)
        val port = authority.substring(colonIndex + 1)
        if (host.isEmpty() || port.isEmpty() || !port.all { it.isDigit() }) return null

        val portValue = port.toIntOrNull() ?: return null
        if (portValue !in 1..65535) return null
        return host to portValue.toString()
    }

    private fun normalizeDomainHost(host: String): String? {
        if (host.isEmpty()) return null
        if (host.equals("localhost", ignoreCase = true)) return null
        if (host.endsWith(".localhost", ignoreCase = true)) return null
        if (host.endsWith(".local", ignoreCase = true)) return null
        if (host.startsWith("-") || host.endsWith("-")) return null
        if (host.contains("..")) return null
        if (host.any { it.isWhitespace() }) return null

        val ascii = try {
            IDN.toASCII(host, IDN.USE_STD3_ASCII_RULES)
        } catch (_: IllegalArgumentException) {
            return null
        }
        val normalized = ascii.lowercase()

        if (normalized.isEmpty() || normalized.length > 253) return null
        if (normalized.endsWith('.')) return null
        if (isIpv4Literal(normalized) || isIpv6Literal(normalized)) return null

        val labels = normalized.split('.')
        if (labels.size < 2) return null
        if (labels.last().length < 2) return null
        if (labels.any { it.isEmpty() || it.length > 63 }) return null
        if (labels.any { it.startsWith("-") || it.endsWith("-") }) return null
        if (labels.any { label -> label.any { !it.isLetterOrDigit() && it != '-' } }) return null
        if (labels.last().all { it.isDigit() }) return null
        if (!normalized.any { it.isLetter() }) return null

        return normalized
    }

    private fun isIpv4Literal(value: String): Boolean {
        val parts = value.split('.')
        if (parts.size != 4) return false
        return parts.all { part ->
            part.isNotEmpty() &&
                part.length <= 3 &&
                part.all { it.isDigit() } &&
                part.toIntOrNull() in 0..255
        }
    }

    private fun isIpv6Literal(value: String): Boolean {
        return value.contains(':')
    }
}
