package com.smsclassifier.app.util

import android.Manifest
import android.app.NotificationManager
import android.os.Build
import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Manual device-inspection harness: posts a representative OTP notification so
 * QA can inspect the expanded layout, copy button, and warning visibility.
 */
@RunWith(AndroidJUnit4::class)
class NotificationHelperSmokeTest {

    @Test
    fun postRepresentativeOtpNotification_forInspection() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            instrumentation.uiAutomation.grantRuntimePermission(
                context.packageName,
                Manifest.permission.POST_NOTIFICATIONS
            )
        }

        NotificationHelper.showNewMessageNotification(
            context = context,
            messageId = 910_001L,
            sender = "VM-SBIOTP",
            body = "Your OTP is 482917 for SBI UPI login. Do not share it with anyone.",
            threadId = 91_000L
        )

        val manager = context.getSystemService(NotificationManager::class.java)
        val deadline = SystemClock.elapsedRealtime() + 2_000L
        var posted = manager.activeNotifications.firstOrNull { it.id == 910_001 }
        while (posted == null && SystemClock.elapsedRealtime() < deadline) {
            SystemClock.sleep(50L)
            posted = manager.activeNotifications.firstOrNull { it.id == 910_001 }
        }
        assertNotNull(posted)
        assertNull(posted?.notification?.extras?.getCharSequence("android.subText"))
        val actionTitles = posted?.notification?.actions.orEmpty().map { it.title.toString() }
        assertEquals(1, actionTitles.count { it == "Copy OTP" })
        assertFalse(actionTitles.any { it == "Open" })
        assertFalse(manager.activeNotifications.any { it.id == 0 })
    }
}
