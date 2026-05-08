package com.smsclassifier.app.util

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.widget.RemoteViews
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.smsclassifier.app.BuildConfig
import com.smsclassifier.app.MainActivity
import com.smsclassifier.app.R
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.NotificationDebugLogEntity
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
            .setContentTitle(if (otpCode != null) "$otpCode  •  OTP from $displayName" else displayName)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .setGroup(NOTIFICATION_GROUP)
            .setShowWhen(true)

        if (otpCode != null) {
            val collapsed = RemoteViews(context.packageName, R.layout.notification_otp_collapsed)
            collapsed.setTextViewText(R.id.notif_otp_sender, "OTP from $displayName")
            collapsed.setTextViewText(R.id.notif_otp_code, otpCode)

            val expanded = RemoteViews(context.packageName, R.layout.notification_otp_expanded)
            expanded.setTextViewText(R.id.notif_otp_sender, "OTP from $displayName")
            expanded.setTextViewText(R.id.notif_otp_code, otpCode)
            expanded.setTextViewText(R.id.notif_otp_body, body)

            builder
                .setContentText(body)
                .setSubText("Autofill code: $otpCode")
                .setCustomContentView(collapsed)
                .setCustomBigContentView(expanded)
                .setStyle(NotificationCompat.DecoratedCustomViewStyle())

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

        val notification = builder.build()
        if (otpCode != null) {
            notification.extras.putCharSequence(NotificationCompat.EXTRA_BIG_TEXT, body)
            notification.extras.putCharSequence(NotificationCompat.EXTRA_TEXT, body)
        }
        NotificationManagerCompat.from(context).notify(messageId.toInt(), notification)
        if (BuildConfig.DEBUG) {
            captureDebugSnapshot(
                context = context,
                notification = notification,
                messageId = messageId,
                sender = sender,
                body = body,
                otpCode = otpCode,
                channelId = channelId
            )
        }
    }

    private fun captureDebugSnapshot(
        context: Context,
        notification: android.app.Notification,
        messageId: Long,
        sender: String,
        body: String,
        otpCode: String?,
        channelId: String
    ) {
        if (!BuildConfig.DEBUG) return
        val extras = notification.extras
        val styleClass = extras.getString(NotificationCompat.EXTRA_TEMPLATE)
            ?.substringAfterLast('.')
            ?: "Unknown"
        val entity = NotificationDebugLogEntity(
            messageId = messageId,
            sender = sender,
            isOtp = otpCode != null,
            otpCode = otpCode,
            channelId = channelId,
            styleClass = styleClass,
            categoryStr = notification.category,
            priority = notification.priority,
            extraTitle = extras.getCharSequence(NotificationCompat.EXTRA_TITLE)?.toString(),
            extraText = extras.getCharSequence(NotificationCompat.EXTRA_TEXT)?.toString(),
            extraBigText = extras.getCharSequence(NotificationCompat.EXTRA_BIG_TEXT)?.toString(),
            extraSubText = extras.getCharSequence(NotificationCompat.EXTRA_SUB_TEXT)?.toString(),
            hasCustomContentView = notification.contentView != null,
            hasCustomBigContentView = notification.bigContentView != null,
            rawBody = body
        )
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val dao = AppDatabase.getDatabase(context.applicationContext)
                    .notificationDebugLogDao()
                dao.insert(entity)
                dao.pruneOldest()
            } catch (t: Throwable) {
                AppLog.w("NotificationHelper", "Failed to capture debug snapshot: ${t.message}", t)
            }
        }
    }

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
