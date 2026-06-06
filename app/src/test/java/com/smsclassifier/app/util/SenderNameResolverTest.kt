package com.smsclassifier.app.util

import org.junit.Assert.assertEquals
import org.junit.Test

class SenderNameResolverTest {

    @Test
    fun resolve_stripsJxDltRoutePrefixForIciciSender() {
        assertEquals("ICICI Bank", SenderNameResolver.resolve("JX-ICICIT"))
    }

    @Test
    fun resolve_stripsVkDltRoutePrefixForSbiOtpSender() {
        assertEquals("SBI", SenderNameResolver.resolve("VK-SBIOTP"))
    }
}
