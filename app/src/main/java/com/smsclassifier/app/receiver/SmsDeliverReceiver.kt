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
        Log.d(TAG, "SmsDeliverReceiver triggered with action=${intent.action}")
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
                Log.d(TAG, "Received SMS from $sender length=${body.length}")

                val messageEntity = MessageEntity(
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
                val newId = database.messageDao().insert(messageEntity)
                Log.d(TAG, "Inserted message $newId and enqueuing worker")
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
