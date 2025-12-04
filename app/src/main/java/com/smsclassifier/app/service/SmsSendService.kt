package com.smsclassifier.app.service

import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.IBinder
import android.telephony.SmsManager
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.util.AppLog
import com.smsclassifier.app.util.ThreadUtils
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

class SmsSendService : Service() {
    private val scope = CoroutineScope(Dispatchers.IO)
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        try {
            val address = intent?.getStringExtra(EXTRA_PHONE_NUMBER)
                ?: intent?.data?.schemeSpecificPart
            val message = intent?.getStringExtra(EXTRA_SMS_MESSAGE_BODY)
                ?: intent?.getStringExtra(Intent.EXTRA_TEXT)

            if (!address.isNullOrBlank() && !message.isNullOrBlank()) {
                val smsManager = SmsManager.getDefault()
                val timestamp = System.currentTimeMillis()
                val threadId = ThreadUtils.calculateThreadId(address)
                
                // Create sent message entity
                val sentMessage = MessageEntity(
                    sender = address,  // For sent messages, sender is the recipient
                    body = message,
                    ts = timestamp,
                    threadId = threadId,
                    type = 4, // 4 = outbox (pending)
                    read = true, // Sent messages are considered read
                    seen = true,
                    status = -1, // -1 = pending
                    serviceCenter = null,
                    dateSent = timestamp,
                    language = null,
                    featuresJson = null,
                    isOtp = null,
                    otpIntent = null,
                    isPhishing = null,
                    phishScore = null,
                    reasonsJson = null,
                    reviewed = false,
                    version = 1
                )
                
                // Save to database first (synchronously to get message ID)
                var messageId: Long = -1
                try {
                    val database = AppDatabase.getDatabase(applicationContext)
                    messageId = runBlocking { database.messageDao().insert(sentMessage) }
                    AppLog.d(TAG, "Saved sent message to database with id=$messageId")
                } catch (e: Exception) {
                    AppLog.e(TAG, "Failed to save sent message", e)
                }
                
                // Register receiver for delivery status
                val sentIntent = PendingIntent.getBroadcast(
                    this,
                    address.hashCode(),
                    Intent(ACTION_SMS_SENT).apply {
                        putExtra(EXTRA_MESSAGE_ID, messageId)
                        putExtra(EXTRA_ADDRESS, address)
                    },
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
                
                val deliveredIntent = PendingIntent.getBroadcast(
                    this,
                    address.hashCode() + 1,
                    Intent(ACTION_SMS_DELIVERED).apply {
                        putExtra(EXTRA_MESSAGE_ID, messageId)
                        putExtra(EXTRA_ADDRESS, address)
                    },
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
                
                // Send SMS
                smsManager.sendTextMessage(address, null, message, sentIntent, deliveredIntent)
                AppLog.d(TAG, "Sent SMS to $address")
                
                // Update status to sent after sending
                if (messageId > 0) {
                    scope.launch {
                        try {
                            val database = AppDatabase.getDatabase(applicationContext)
                            val updatedMessage = sentMessage.copy(
                                id = messageId,
                                type = 2, // 2 = sent
                                status = 0 // 0 = complete
                            )
                            database.messageDao().update(updatedMessage)
                        } catch (e: Exception) {
                            AppLog.e(TAG, "Failed to update sent message status", e)
                        }
                    }
                }
            } else {
                AppLog.w(TAG, "Missing address or message in SmsSendService")
            }
        } catch (t: Throwable) {
            AppLog.e(TAG, "Failed to send SMS", t)
        } finally {
            stopSelf(startId)
        }
        return START_NOT_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        private const val TAG = "SmsSendService"
        private const val EXTRA_PHONE_NUMBER = "android.intent.extra.PHONE_NUMBER"
        private const val EXTRA_SMS_MESSAGE_BODY = "android.intent.extra.TEXT"
        const val ACTION_SMS_SENT = "com.smsclassifier.app.SMS_SENT"
        const val ACTION_SMS_DELIVERED = "com.smsclassifier.app.SMS_DELIVERED"
        const val EXTRA_MESSAGE_ID = "message_id"
        const val EXTRA_ADDRESS = "address"
    }
}

// Broadcast receivers for SMS send status
class SmsSentReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        when (resultCode) {
            android.app.Activity.RESULT_OK -> {
                AppLog.d(TAG, "SMS sent successfully")
            }
            else -> {
                AppLog.w(TAG, "SMS send failed with code: $resultCode")
                // Update message status to failed
                val messageId = intent.getLongExtra(SmsSendService.EXTRA_MESSAGE_ID, -1)
                if (messageId > 0) {
                    CoroutineScope(Dispatchers.IO).launch {
                        try {
                            val database = AppDatabase.getDatabase(context)
                            val message = database.messageDao().getById(messageId)
                            message?.let {
                                database.messageDao().update(it.copy(
                                    type = 5, // 5 = failed
                                    status = resultCode
                                ))
                            }
                        } catch (e: Exception) {
                            AppLog.e(TAG, "Failed to update message status", e)
                        }
                    }
                }
            }
        }
    }
    
    companion object {
        private const val TAG = "SmsSentReceiver"
    }
}

class SmsDeliveredReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        when (resultCode) {
            android.app.Activity.RESULT_OK -> {
                AppLog.d(TAG, "SMS delivered")
                // Message is already marked as sent, delivery is just confirmation
            }
            else -> {
                AppLog.d(TAG, "SMS delivery status: $resultCode")
            }
        }
    }
    
    companion object {
        private const val TAG = "SmsDeliveredReceiver"
    }
}
