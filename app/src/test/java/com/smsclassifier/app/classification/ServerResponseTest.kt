package com.smsclassifier.app.classification

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ServerResponseTest {
    @Test
    fun decodesLinkReputationVerdicts() {
        val response = Json.decodeFromString<ServerResponse>(
            """
                {
                  "isOtp": false,
                  "otpIntent": "NOT_OTP",
                  "isPhishing": false,
                  "phishScore": 0.08,
                  "reasons": [],
                  "linkVerdicts": [
                    {
                      "url": "https://example.com/pay",
                      "host": "example.com",
                      "status": "NO_MATCH",
                      "threatTypes": [],
                      "checkedAtEpochMs": 1700000000000,
                      "latencyMs": 42.5
                    }
                  ]
                }
            """.trimIndent()
        )

        assertEquals(1, response.linkVerdicts.size)
        assertEquals("example.com", response.linkVerdicts.single().host)
        assertEquals("NO_MATCH", response.linkVerdicts.single().status)
    }

    @Test
    fun olderResponseWithoutLinkVerdictsRemainsCompatible() {
        val response = Json.decodeFromString<ServerResponse>(
            """
                {
                  "isOtp": true,
                  "otpIntent": "APP_LOGIN_OTP",
                  "isPhishing": false,
                  "phishScore": 0.05,
                  "reasons": []
                }
            """.trimIndent()
        )

        assertTrue(response.linkVerdicts.isEmpty())
    }
}
