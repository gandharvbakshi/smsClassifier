package com.smsclassifier.app.util

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.text.Html
import android.text.Spanned
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.smsclassifier.app.MainActivity
import com.smsclassifier.app.R
import com.smsclassifier.app.data.SettingsRepository
import com.smsclassifier.app.util.ClassificationUtils.extractOtpForCopy
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * Builds rich SMS notifications. For OTP messages we use a prominent layout with the
 * OTP code rendered in very large bold text so it can be read at a glance from the
 * lock screen / notification shade.
 */
object NotificationHelper {
    private const val CHANNEL_ID_DEFAULT = "sms_notifications"
    private const val CHANNEL_NAME_DEFAULT = "SMS Notifications"
    private const val CHANNEL_ID_OTP = "sms_otp_notifications"
    private const val CHANNEL_NAME_OTP = "OTP Notifications"
    private const val NOTIFICATION_GROUP = "sms_group"

    fun createNotificationChannel(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return

        val notificationManager =
            context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        val defaultChannel = NotificationChannel(
            CHANNEL_ID_DEFAULT,
            CHANNEL_NAME_DEFAULT,
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Notifications for incoming SMS messages"
            enableVibration(true)
            enableLights(true)
        }
        notificationManager.createNotificationChannel(defaultChannel)

        val otpChannel = NotificationChannel(
            CHANNEL_ID_OTP,
            CHANNEL_NAME_OTP,
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "High-priority notifications for OTP / verification codes"
            enableVibration(true)
            enableLights(true)
            setBypassDnd(false)
        }
        notificationManager.createNotificationChannel(otpChannel)
    }

    fun showNewMessageNotification(
        context: Context,
        messageId: Long,
        sender: String,
        body: String,
        threadId: Long
    ) {
        createNotificationChannel(context)

        val notificationManager = NotificationManagerCompat.from(context)
        if (!notificationManager.areNotificationsEnabled()) {
            AppLog.w("NotificationHelper", "Notifications are disabled by user")
            return
        }

        val otpCode = extractOtpForCopy(body, sender, null)
        val channelId = if (otpCode != null) CHANNEL_ID_OTP else CHANNEL_ID_DEFAULT

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = notificationManager.getNotificationChannel(channelId)
            if (channel?.importance == NotificationManager.IMPORTANCE_NONE) {
                AppLog.w("NotificationHelper", "Notification channel is disabled")
                return
            }
        }

        AppLog.d("NotificationHelper", "Showing notification for message $messageId from $sender (otp=${otpCode != null})")

        // Show immediately with raw sender, then update with contact name if found.
        renderNotification(
            context = context,
            messageId = messageId,
            displayName = sender,
            sender = sender,
            body = body,
            threadId = threadId,
            otpCode = otpCode,
            channelId = channelId
        )

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val contactName = ContactHelper.getContactName(context, sender)
                if (!contactName.isNullOrBlank() && contactName != sender) {
                    renderNotification(
                        context = context,
                        messageId = messageId,
                        displayName = contactName,
                        sender = sender,
                        body = body,
                        threadId = threadId,
                        otpCode = otpCode,
                        channelId = channelId
                    )
                }
            } catch (e: Exception) {
                AppLog.w("NotificationHelper", "Failed to load contact name for notification", e)
            }
        }

        showSummaryNotification(context, channelId)
    }

    private fun renderNotification(
        context: Context,
        messageId: Long,
        displayName: String,
        sender: String,
        body: String,
        threadId: Long,
        otpCode: String?,
        channelId: String
    ) {
        val settingsRepository = SettingsRepository(context)
        val soundEnabled = settingsRepository.notificationSoundEnabled
        val vibrationEnabled = settingsRepository.notificationVibrationEnabled

        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            putExtra("threadId", threadId)
            putExtra("openThread", true)
        }
        val pendingIntent = PendingIntent.getActivity(
            context,
            messageId.toInt(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val builder = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_email)
            .setContentTitle(if (otpCode != null) "OTP from $displayName" else displayName)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(if (otpCode != null) NotificationCompat.CATEGORY_MESSAGE else NotificationCompat.CATEGORY_MESSAGE)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .setGroup(NOTIFICATION_GROUP)
            .setShowWhen(true)

        if (otpCode != null) {
            // Big, bold, large OTP rendering. Android renders <big><b> in BigTextStyle text,
            // so the code itself becomes the focal point.
            val bigText: Spanned = Html.fromHtml(
                "<big><big><big><b>$otpCode</b></big></big></big><br/><br/>" +
                    "<small>${escape(body)}</small>",
                Html.FROM_HTML_MODE_LEGACY
            )
            builder
                .setContentText("Tap to copy: $otpCode")
                .setStyle(
                    NotificationCompat.BigTextStyle()
                        .setBigContentTitle("OTP from $displayName")
                        .setSummaryText("Verification code")
                        .bigText(bigText)
                )
                .setTicker("OTP $otpCode from $displayName")

            // Primary "Copy OTP" action — make it the first/most-prominent action.
            val copyOtpIntent = Intent(context, CopyOtpReceiver::class.java).apply {
                putExtra(CopyOtpReceiver.EXTRA_OTP_CODE, otpCode)
            }
            val copyOtpPendingIntent = PendingIntent.getBroadcast(
                context,
                (messageId + 30000).toInt(),
                copyOtpIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            builder.addAction(
                android.R.drawable.ic_menu_save,
                "Copy $otpCode",
                copyOtpPendingIntent
            )
        } else {
            builder
                .setContentText(body)
                .setStyle(NotificationCompat.BigTextStyle().bigText(body))

            val replyIntent = Intent(context, QuickReplyReceiver::class.java).apply {
                putExtra("threadId", threadId)
                putExtra("sender", sender)
            }
            val replyPendingIntent = PendingIntent.getBroadcast(
                context,
                (messageId + 10000).toInt(),
                replyIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            val markReadIntent = Intent(context, MarkAsReadReceiver::class.java).apply {
                putExtra("threadId", threadId)
            }
            val markReadPendingIntent = PendingIntent.getBroadcast(
                context,
                (messageId + 20000).toInt(),
                markReadIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            builder
                .addAction(android.R.drawable.ic_menu_send, "Reply", replyPendingIntent)
                .addAction(android.R.drawable.ic_menu_view, "Mark as read", markReadPendingIntent)
        }

        if (!soundEnabled) builder.setSilent(true)
        if (!vibrationEnabled) builder.setVibrate(longArrayOf(0))

        NotificationManagerCompat.from(context).notify(messageId.toInt(), builder.build())
    }

    private fun escape(input: String): String =
        input.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    private fun showSummaryNotification(context: Context, channelId: String) {
        val summaryIntent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        val summaryPendingIntent = PendingIntent.getActivity(
            context,
            0,
            summaryIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val summaryNotification = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_email)
            .setContentTitle("New Messages")
            .setGroup(NOTIFICATION_GROUP)
            .setGroupSummary(true)
            .setContentIntent(summaryPendingIntent)
            .setAutoCancel(true)
            .build()

        NotificationManagerCompat.from(context).notify(0, summaryNotification)
    }

    fun cancelNotification(context: Context, notificationId: Int) {
        NotificationManagerCompat.from(context).cancel(notificationId)
    }

    fun cancelAllNotifications(context: Context) {
        NotificationManagerCompat.from(context).cancelAll()
    }
}
