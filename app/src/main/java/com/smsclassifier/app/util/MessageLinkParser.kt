package com.smsclassifier.app.util

/**
 * Extracts plain-text HTTP(S) links from SMS bodies.
 *
 * The parser is intentionally conservative:
 * - only literal http:// and https:// prefixes are recognized
 * - bare domains and other schemes are ignored
 * - common sentence punctuation at the end of a URL is trimmed
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

    fun findLinks(text: String): List<LinkMatch> {
        if (text.isEmpty()) return emptyList()

        val matches = ArrayList<LinkMatch>()
        var index = 0
        while (index < text.length) {
            val schemeStart = when {
                text.regionMatches(index, "https://", 0, "https://".length, ignoreCase = true) -> index
                text.regionMatches(index, "http://", 0, "http://".length, ignoreCase = true) -> index
                else -> {
                    index++
                    continue
                }
            }

            if (schemeStart > 0 && text[schemeStart - 1].isLetterOrDigit()) {
                index = schemeStart + 1
                continue
            }

            var end = schemeStart
            while (end < text.length && !text[end].isWhitespace()) {
                end++
            }

            var trimmedEnd = end
            while (trimmedEnd > schemeStart && text[trimmedEnd - 1] in trailingPunctuation) {
                trimmedEnd--
            }

            if (trimmedEnd > schemeStart) {
                matches += LinkMatch(
                    url = text.substring(schemeStart, trimmedEnd),
                    start = schemeStart,
                    endExclusive = trimmedEnd
                )
            }

            index = if (end > schemeStart) end else schemeStart + 1
        }

        return matches
    }
}
