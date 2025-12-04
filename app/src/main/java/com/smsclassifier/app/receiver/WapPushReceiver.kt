package com.smsclassifier.app.receiver

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.smsclassifier.app.MainActivity
import com.smsclassifier.app.R
import com.smsclassifier.app.util.AppLog

class WapPushReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        AppLog.d(TAG, "Received WAP push intent: ${intent.action}")
        
        // MMS support is not fully implemented yet
        // Show a notification to the user
        showMmsNotSupportedNotification(context)
        
        // For MVP, we just acknowledge receipt but don't process
        // This satisfies the requirement to have MMS receivers registered
    }
    
    private fun showMmsNotSupportedNotification(context: Context) {
        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        
        // Create notification channel for Android O+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "MMS Notifications",
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "Notifications for MMS messages"
            }
            notificationManager.createNotificationChannel(channel)
        }
        
        // Create intent to open app
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        val pendingIntent = PendingIntent.getActivity(
            context,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("MMS Received")
            .setContentText("MMS support is not fully implemented yet. Full MMS support coming soon.")
            .setStyle(NotificationCompat.BigTextStyle()
                .bigText("An MMS message was received but cannot be displayed. Full MMS support including media attachments will be available in a future update."))
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build()
        
        notificationManager.notify(NOTIFICATION_ID, notification)
    }

    companion object {
        private const val TAG = "WapPushReceiver"
        private const val CHANNEL_ID = "mms_notifications"
        private const val NOTIFICATION_ID = 1001
    }
}
