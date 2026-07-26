package com.smsclassifier.app.util

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MessageLinkParserTest {

    @Test
    fun findLinks_keepsExistingHttpBehavior() {
        val matches = MessageLinkParser.findLinks(
            "Open HTTPS://example.com or HTTP://example.org."
        )

        assertEquals(listOf("https://example.com", "http://example.org"), matches.map { it.url })
        assertEquals("https://example.com", matches[0].url)
        assertEquals("http://example.org", matches[1].url)
    }

    @Test
    fun findLinks_normalizesBareAndWwwLinksToHttpsAndPreservesDisplayRange() {
        val text = "Read r13.example.co.in/path?q=1 and www.demo.example/pay."
        val matches = MessageLinkParser.findLinks(text)

        assertEquals(2, matches.size)

        assertEquals("https://r13.example.co.in/path?q=1", matches[0].url)
        assertEquals("r13.example.co.in/path?q=1", text.substring(matches[0].start, matches[0].endExclusive))
        assertEquals(text.indexOf("r13.example.co.in/path?q=1"), matches[0].start)
        assertEquals(text.indexOf("r13.example.co.in/path?q=1") + "r13.example.co.in/path?q=1".length, matches[0].endExclusive)

        assertEquals("https://www.demo.example/pay", matches[1].url)
        assertEquals("www.demo.example/pay", text.substring(matches[1].start, matches[1].endExclusive))
        assertEquals(text.indexOf("www.demo.example/pay"), matches[1].start)
        assertEquals(text.indexOf("www.demo.example/pay") + "www.demo.example/pay".length, matches[1].endExclusive)
    }

    @Test
    fun findLinks_handlesMultipleLinksAndTrimsTrailingPunctuation() {
        val text = "Try https://example.com/path), example.org/help!, and www.shop.example/now."
        val matches = MessageLinkParser.findLinks(text)

        assertEquals(3, matches.size)
        assertEquals("https://example.com/path", matches[0].url)
        assertEquals("https://example.com/path", text.substring(matches[0].start, matches[0].endExclusive))
        assertEquals("https://example.org/help", matches[1].url)
        assertEquals("https://www.shop.example/now", matches[2].url)
    }

    @Test
    fun findLinks_ignoresEmailsLookalikesSchemesAndIpHosts() {
        val matches = MessageLinkParser.findLinks(
            "Email a.b@example.com, hxxp://bad.example, javascript:alert(1), http://127.0.0.1, http://10.0.0.7, and ftp://files.example."
        )

        assertTrue(matches.toString(), matches.isEmpty())
    }

    @Test
    fun findLinks_ignoresPrivateAndUserInfoUrls() {
        val matches = MessageLinkParser.findLinks(
            "http://user:pass@example.com http://localhost/admin http://192.168.1.1/app"
        )

        assertTrue(matches.toString(), matches.isEmpty())
    }

    @Test
    fun findLinks_rejectsAmbiguousAndInvalidBareDomains() {
        val matches = MessageLinkParser.findLinks(
            "example,com www.example..com foo.bar- http://-bad.example http://example-.com"
        )

        assertTrue(matches.toString(), matches.isEmpty())
    }

    @Test
    fun findLinks_handlesIdnDomains() {
        val matches = MessageLinkParser.findLinks(
            "Check münich.example/path and https://xn--mnich-kva.example/ok."
        )

        assertEquals(2, matches.size)
        assertEquals("https://xn--mnich-kva.example/path", matches[0].url)
        assertEquals("https://xn--mnich-kva.example/ok", matches[1].url)
    }

    @Test
    fun findLinks_canonicalizesQueriesFragmentsAndShortPortsLikeBackend() {
        val matches = MessageLinkParser.findLinks(
            "example.com?token=abc example.org:8/pay?x=1 demo.example/path#section"
        )

        assertEquals(
            listOf(
                "https://example.com?token=abc",
                "https://example.org:8/pay?x=1",
                "https://demo.example/path"
            ),
            matches.map { it.url }
        )
    }

    @Test
    fun findLinks_rejectsInvalidPortsAndOneCharacterTlds() {
        val matches = MessageLinkParser.findLinks(
            "example.com:0/pay example.com:70000/pay example.com:123456/pay a.b"
        )

        assertTrue(matches.toString(), matches.isEmpty())
    }

    @Test
    fun findLinks_trimsSentencePunctuationWithoutEatingSurroundingText() {
        val text = "(example.com/path)."
        val matches = MessageLinkParser.findLinks(text)

        assertEquals(1, matches.size)
        assertEquals("https://example.com/path", matches[0].url)
        assertEquals("example.com/path", text.substring(matches[0].start, matches[0].endExclusive))
        assertEquals('(', text.first())
        assertEquals('.', text.last())
        assertFalse(matches[0].endExclusive > text.length)
    }
}
