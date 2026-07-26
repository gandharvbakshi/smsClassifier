package com.smsclassifier.app.util

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LinkInteractionPolicyTest {
    @Test
    fun allowsOnlyNoMatchVerdictsForNewSafeMessages() {
        assertTrue(
            LinkInteractionPolicy.isAllowed(
                scamLikely = false,
                linkVerdictsJson = """
                    [{"url":"https://example.com","host":"example.com","status":"NO_MATCH"}]
                """.trimIndent(),
                messageBody = "Open example.com"
            )
        )

        listOf(
            "MALICIOUS",
            "UNAVAILABLE",
            "NOT_CHECKED",
            "INVALID"
        ).forEach { status ->
            assertFalse(
                LinkInteractionPolicy.isAllowed(
                    scamLikely = false,
                    linkVerdictsJson = """
                        [{"url":"https://example.com","host":"example.com","status":"$status"}]
                    """.trimIndent(),
                    messageBody = "Open example.com"
                )
            )
        }
    }

    @Test
    fun blocksScamsEmptyResultsMixedResultsAndMalformedData() {
        assertFalse(
            LinkInteractionPolicy.isAllowed(
                scamLikely = true,
                linkVerdictsJson = """
                    [{"url":"https://example.com","host":"example.com","status":"NO_MATCH"}]
                """.trimIndent(),
                messageBody = "Open example.com"
            )
        )
        assertFalse(LinkInteractionPolicy.isAllowed(false, "[]", "Open example.com"))
        assertFalse(LinkInteractionPolicy.isAllowed(false, "not-json", "Open example.com"))
        assertFalse(
            LinkInteractionPolicy.isAllowed(
                false,
                """
                    [
                      {"url":"https://one.example","host":"one.example","status":"NO_MATCH"},
                      {"url":"https://two.example","host":"two.example","status":"UNAVAILABLE"}
                    ]
                """.trimIndent(),
                "Open one.example and two.example"
            )
        )
    }

    @Test
    fun blocksWhenVisibleLinksDoNotExactlyMatchCheckedUrls() {
        val oneVerdict = """
            [{"url":"https://example.com","host":"example.com","status":"NO_MATCH"}]
        """.trimIndent()

        assertFalse(
            LinkInteractionPolicy.isAllowed(
                false,
                oneVerdict,
                "Open example.com?token=unchecked"
            )
        )
        assertFalse(
            LinkInteractionPolicy.isAllowed(
                false,
                oneVerdict,
                "Open example.com and demo.example"
            )
        )
    }

    @Test
    fun preservesLegacyNullVerdictBehavior() {
        assertTrue(LinkInteractionPolicy.isAllowed(false, null, "Open example.com"))
    }
}
