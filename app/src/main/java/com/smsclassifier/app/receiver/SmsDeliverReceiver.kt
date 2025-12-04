package com.smsclassifier.app.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.Telephony
import android.telephony.SmsMessage
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.util.AppLog
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.util.ThreadUtils
import com.smsclassifier.app.util.NotificationHelper
import com.smsclassifier.app.work.ClassificationWorker
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class SmsDeliverReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        AppLog.d(TAG, "SmsDeliverReceiver triggered with action=${intent.action}")
        if (Telephony.Sms.Intents.SMS_DELIVER_ACTION != intent.action) return

        val pendingResult = goAsync()
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
                if (messages.isNullOrEmpty()) {
                    AppLog.w(TAG, "No messages received")
                    pendingResult.finish()
                    return@launch
                }

                val sender = messages.firstOrNull()?.displayOriginatingAddress ?: "UNKNOWN"
                val timestamp = messages.firstOrNull()?.timestampMillis ?: System.currentTimeMillis()
                val body = messages.joinToString(separator = "") { it.displayMessageBody ?: "" }
                val serviceCenter = messages.firstOrNull()?.serviceCenterAddress
                AppLog.d(TAG, "Received SMS from $sender, length=${body.length}")

                // Calculate thread ID from sender phone number
                val threadId = ThreadUtils.calculateThreadId(sender)

                val messageEntity = MessageEntity(
                    sender = sender,
                    body = body,
                    ts = timestamp,
                    threadId = threadId,
                    type = 1, // 1 = received/incoming
                    read = false,
                    seen = false,
                    status = null,
                    serviceCenter = serviceCenter,
                    dateSent = null,
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

                val database = AppDatabase.getDatabase(context.applicationContext)
                val newId = database.messageDao().insert(messageEntity)
                AppLog.d(TAG, "Inserted message $newId and enqueuing worker")
                
                // Show notification for new message
                NotificationHelper.showNewMessageNotification(
                    context.applicationContext,
                    newId,
                    sender,
                    body,
                    threadId
                )
                
                ClassificationWorker.enqueue(context.applicationContext)
            } catch (t: Throwable) {
                AppLog.e(TAG, "Failed to handle incoming SMS", t)
            } finally {
                pendingResult.finish()
            }
        }
    }

    companion object {
        private const val TAG = "SmsDeliverReceiver"
    }
}
