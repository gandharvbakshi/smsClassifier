package com.smsclassifier.app.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.Telephony
import android.telephony.SmsMessage
import android.util.Log
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.work.ClassificationWorker
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class SmsDeliverReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (Telephony.Sms.Intents.SMS_DELIVER_ACTION != intent.action) return

        val pendingResult = goAsync()
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
                if (messages.isNullOrEmpty()) {
                    Log.w(TAG, "No messages received")
                    pendingResult.finish()
                    return@launch
                }

                val sender = messages.firstOrNull()?.displayOriginatingAddress ?: "UNKNOWN"
                val timestamp = messages.firstOrNull()?.timestampMillis ?: System.currentTimeMillis()
                val body = messages.joinToString(separator = "") { it.displayMessageBody ?: "" }

                val messageEntity = MessageEntity(
                    id = 0,
                    sender = sender,
                    body = body,
                    ts = timestamp,
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
                database.messageDao().insert(messageEntity)
                ClassificationWorker.enqueue(context.applicationContext)
            } catch (t: Throwable) {
                Log.e(TAG, "Failed to handle incoming SMS", t)
            } finally {
                pendingResult.finish()
            }
        }
    }

    companion object {
        private const val TAG = "SmsDeliverReceiver"
    }
}
