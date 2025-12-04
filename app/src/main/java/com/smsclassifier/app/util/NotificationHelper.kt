package com.smsclassifier.app.util

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.smsclassifier.app.MainActivity
import com.smsclassifier.app.R
import com.smsclassifier.app.data.SettingsRepository

object NotificationHelper {
    private const val CHANNEL_ID = "sms_notifications"
    private const val CHANNEL_NAME = "SMS Notifications"
    private const val NOTIFICATION_GROUP = "sms_group"
    
    fun createNotificationChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Notifications for incoming SMS messages"
                enableVibration(true)
                enableLights(true)
            }
            val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }
    
    fun showNewMessageNotification(
        context: Context,
        messageId: Long,
        sender: String,
        body: String,
        threadId: Long
    ) {
        // Ensure notification channel exists
        createNotificationChannel(context)
        
        // Check if notifications are enabled
        val notificationManager = NotificationManagerCompat.from(context)
        if (!notificationManager.areNotificationsEnabled()) {
            AppLog.w("NotificationHelper", "Notifications are disabled by user")
            // Don't show notification if user has disabled them
            return
        }
        
        // Check if channel is enabled (Android 8.0+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = notificationManager.getNotificationChannel(CHANNEL_ID)
            if (channel?.importance == NotificationManager.IMPORTANCE_NONE) {
                AppLog.w("NotificationHelper", "Notification channel is disabled")
                // Don't show notification if channel is disabled
                return
            }
        }
        
        AppLog.d("NotificationHelper", "Showing notification for message $messageId from $sender")
        
        // Read notification preferences from settings
        val settingsRepository = SettingsRepository(context)
        val soundEnabled = settingsRepository.notificationSoundEnabled
        val vibrationEnabled = settingsRepository.notificationVibrationEnabled
        
        // Intent to open thread view
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
        
        // Quick reply action
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
        
        val notificationBuilder = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_email)
            .setContentTitle(sender)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .setGroup(NOTIFICATION_GROUP)
            .addAction(
                android.R.drawable.ic_menu_send,
                "Reply",
                replyPendingIntent
            )
        
        // Apply sound and vibration settings
        if (!soundEnabled) {
            notificationBuilder.setSilent(true)
        }
        if (!vibrationEnabled) {
            notificationBuilder.setVibrate(longArrayOf(0)) // No vibration
        }
        
        val notification = notificationBuilder.build()
        
        NotificationManagerCompat.from(context).notify(messageId.toInt(), notification)
        
        // Summary notification for group
        showSummaryNotification(context)
    }
    
    private fun showSummaryNotification(context: Context) {
        val summaryIntent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        val summaryPendingIntent = PendingIntent.getActivity(
            context,
            0,
            summaryIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        val summaryNotification = NotificationCompat.Builder(context, CHANNEL_ID)
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

