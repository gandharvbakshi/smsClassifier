package com.smsclassifier.app.ui

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.util.OtpIntentResolver
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

/** Seeds synthetic, non-private OTP rows for end-to-end visual inspection. */
@RunWith(AndroidJUnit4::class)
class OtpIntentSurfaceSmokeTest {

    @Test
    fun seedRepresentativeOtpMessages_forVisualInspection() = runBlocking {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val dao = AppDatabase.getDatabase(context).messageDao()
        val now = System.currentTimeMillis()
        val messages = listOf(
            otpMessage(
                id = 920_001L,
                sender = "HDFC Bank",
                body = "Your OTP is 481902 for a card payment of INR 1250 at MEDICARE. Never share this OTP.",
                ts = now,
                intent = "BANK_OR_CARD_TXN_OTP",
                isPhishing = true,
                phishScore = 0.91f
            ),
            otpMessage(
                id = 920_002L,
                sender = "HDFC NetBanking",
                body = "Use OTP 662140 to login to HDFC net banking. Never share this OTP.",
                ts = now - 1_000L,
                intent = "FINANCIAL_LOGIN_OTP"
            ),
            otpMessage(
                id = 920_003L,
                sender = "WhatsApp",
                body = "Your WhatsApp OTP is 834291 to move your account to a new phone. Never share it.",
                ts = now - 2_000L,
                intent = "APP_ACCOUNT_CHANGE_OTP"
            ),
            otpMessage(
                id = 920_004L,
                sender = "Porter",
                body = "Your delivery OTP is 537993. Share it only with your courier.",
                ts = now - 3_000L,
                intent = "DELIVERY_OR_SERVICE_OTP"
            ),
            otpMessage(
                id = 920_005L,
                sender = "PhonePe",
                body = "Use OTP 715204 to approve a UPI payment of INR 500. Never share this OTP.",
                ts = now - 4_000L,
                intent = "UPI_TXN_OR_PIN_OTP"
            ),
            otpMessage(
                id = 920_006L,
                sender = "Test App",
                body = "Your OTP is 908172. Valid for 10 minutes.",
                ts = now - 5_000L,
                intent = "GENERIC_APP_ACTION_OTP"
            )
        )

        messages.forEach { dao.insert(it) }

        val stored = messages.map { requireNotNull(dao.getById(it.id)) }
        assertEquals(
            listOf(
                "Bank transaction OTP",
                "Bank login OTP",
                "WhatsApp account change OTP",
                "Courier delivery OTP",
                "UPI payment OTP",
                "OTP"
            ),
            stored.map { OtpIntentResolver.resolve(it).label }
        )
        assertEquals(true, stored.first().isPhishing)
        assertEquals(0.91f, stored.first().phishScore ?: -1f, 0.0001f)
    }

    private fun otpMessage(
        id: Long,
        sender: String,
        body: String,
        ts: Long,
        intent: String,
        isPhishing: Boolean = false,
        phishScore: Float = 0.05f
    ) = MessageEntity(
        id = id,
        sender = sender,
        body = body,
        ts = ts,
        threadId = id,
        isOtp = true,
        otpIntent = intent,
        isPhishing = isPhishing,
        phishScore = phishScore,
        reviewed = true
    )
}
