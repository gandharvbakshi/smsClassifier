package com.smsclassifier.app.util

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class MessageLinkParserTest {

    @Test
    fun findLinks_detectsOnlyHttpAndHttpsUrls() {
        val matches = MessageLinkParser.findLinks(
            "Open https://example.com/path?x=1 and http://foo.test"
        )

        assertEquals(2, matches.size)
        assertEquals("https://example.com/path?x=1", matches[0].url)
        assertEquals("http://foo.test", matches[1].url)
    }

    @Test
    fun findLinks_handlesMultipleLinksWithCorrectOffsets() {
        val text = "First https://a.example one, then http://b.example/two."
        val matches = MessageLinkParser.findLinks(text)

        assertEquals(2, matches.size)
        assertEquals("https://a.example", matches[0].url)
        assertEquals(text.indexOf("https://a.example"), matches[0].start)
        assertEquals(matches[0].start + matches[0].url.length, matches[0].endExclusive)

        assertEquals("http://b.example/two", matches[1].url)
        assertEquals(text.indexOf("http://b.example/two"), matches[1].start)
        assertEquals(matches[1].start + matches[1].url.length, matches[1].endExclusive)
    }

    @Test
    fun findLinks_trimsTrailingSentencePunctuationWithoutEatingText() {
        val matches = MessageLinkParser.findLinks(
            "Check https://example.com/path). Thanks!"
        )

        assertEquals(1, matches.size)
        assertEquals("https://example.com/path", matches[0].url)
        assertTrue(matches[0].endExclusive < "Check https://example.com/path). Thanks!".length)
    }

    @Test
    fun findLinks_ignoresPlainDomainsAndOtherSchemes() {
        val matches = MessageLinkParser.findLinks(
            "Visit example.com, ftp://files.example, and mailto:test@example.com."
        )

        assertTrue(matches.isEmpty())
    }

    @Test
    fun findLinks_acceptsCaseInsensitiveHttpSchemes() {
        val matches = MessageLinkParser.findLinks(
            "Open HTTPS://example.com or HTTP://example.org."
        )

        assertEquals(
            listOf("HTTPS://example.com", "HTTP://example.org"),
            matches.map { it.url }
        )
    }
}
