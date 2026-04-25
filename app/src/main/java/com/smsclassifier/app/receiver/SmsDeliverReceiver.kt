package com.smsclassifier.app.receiver

import android.content.BroadcastReceiver
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.provider.Telephony
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

        // === STEP 1: Parse and persist to system Telephony provider SYNCHRONOUSLY.
        // Other apps (Swiggy, Amazon, Google Play Services SMS Retriever / User Consent)
        // start querying content://sms/inbox the moment they observe a new SMS. If we
        // delay this write into a coroutine, those apps may see an empty inbox and
        // OTP auto-fill will silently fail. Insert is a fast binder call; it is safe
        // to run on the broadcast thread.
        val messages = try {
            Telephony.Sms.Intents.getMessagesFromIntent(intent)
        } catch (t: Throwable) {
            AppLog.e(TAG, "Failed to parse SMS messages from intent", t)
            null
        }
        if (messages.isNullOrEmpty()) {
            AppLog.w(TAG, "No messages received")
            return
        }

        val sender = messages.firstOrNull()?.displayOriginatingAddress ?: "UNKNOWN"
        val timestamp = messages.firstOrNull()?.timestampMillis ?: System.currentTimeMillis()
        val body = messages.joinToString(separator = "") { it.displayMessageBody ?: "" }
        val serviceCenter = messages.firstOrNull()?.serviceCenterAddress
        AppLog.d(TAG, "Received SMS from $sender, length=${body.length}")

        writeToSystemSmsProvider(context, sender, body, timestamp, serviceCenter)

        // === STEP 2: Persist to our app DB, classify, notify (slower) — async.
        val pendingResult = goAsync()
        CoroutineScope(Dispatchers.IO).launch {
            try {
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

    /**
     * Writes the incoming SMS to the system Telephony database (content://sms/inbox).
     *
     * This is REQUIRED for OTP-autofill in other apps (Swiggy, Amazon, banking, etc.).
     * Those apps query the system SMS provider, NOT our custom provider. As the default
     * SMS handler we are responsible for persisting incoming SMS into the system provider
     * — without this step, other apps see an empty inbox.
     */
    private fun writeToSystemSmsProvider(
        context: Context,
        sender: String,
        body: String,
        timestamp: Long,
        serviceCenter: String?
    ) {
        try {
            val values = ContentValues().apply {
                put(Telephony.Sms.ADDRESS, sender)
                put(Telephony.Sms.BODY, body)
                put(Telephony.Sms.DATE, timestamp)
                put(Telephony.Sms.DATE_SENT, timestamp)
                put(Telephony.Sms.READ, 0)
                put(Telephony.Sms.SEEN, 0)
                put(Telephony.Sms.TYPE, Telephony.Sms.MESSAGE_TYPE_INBOX)
                serviceCenter?.let { put(Telephony.Sms.SERVICE_CENTER, it) }
            }
            val uri = context.contentResolver.insert(Telephony.Sms.Inbox.CONTENT_URI, values)
            if (uri != null) {
                AppLog.d(TAG, "Wrote SMS to system provider at $uri")
            } else {
                AppLog.w(TAG, "System SMS provider returned null URI; OTP autofill may not work")
            }
        } catch (t: Throwable) {
            AppLog.e(TAG, "Failed to write SMS to system provider", t)
        }
    }

    companion object {
        private const val TAG = "SmsDeliverReceiver"
    }
}
