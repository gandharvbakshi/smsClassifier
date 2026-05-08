package com.smsclassifier.app.data

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * What our app told the system to render for a single notification, captured
 * the way a NotificationListenerService (e.g. SmsCodeAutofillService) would
 * see it via Notification.extras.
 *
 * Debug-only: only written and read in BuildConfig.DEBUG builds. Used to
 * verify Phase 1 fix (full body in EXTRA_TEXT / EXTRA_BIG_TEXT) without ADB.
 */
@Entity(tableName = "notification_debug_logs")
data class NotificationDebugLogEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val createdAt: Long = System.currentTimeMillis(),
    val messageId: Long,
    val sender: String,
    val isOtp: Boolean,
    val otpCode: String?,
    val channelId: String,
    val styleClass: String,
    val categoryStr: String?,
    val priority: Int,
    val extraTitle: String?,
    val extraText: String?,
    val extraBigText: String?,
    val extraSubText: String?,
    val hasCustomContentView: Boolean,
    val hasCustomBigContentView: Boolean,
    val rawBody: String
)
