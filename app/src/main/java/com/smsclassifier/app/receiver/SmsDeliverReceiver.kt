package com.smsclassifier.app.receiver

import android.content.BroadcastReceiver
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.Telephony
import android.telephony.SmsMessage
import android.telephony.SubscriptionManager
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.util.AppLog
import com.smsclassifier.app.util.NotificationHelper
import com.smsclassifier.app.util.ThreadUtils
import com.smsclassifier.app.work.ClassificationWorker
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class SmsDeliverReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        AppLog.d(TAG, "SmsDeliverReceiver triggered with action=${intent.action}")
        if (Telephony.Sms.Intents.SMS_DELIVER_ACTION != intent.action) return

        // === STEP 1: Parse and persist to system Telephony provider SYNCHRONOUSLY,
        // and write rows that LOOK identical to what AOSP Messaging / Microsoft SMS
        // Organizer write — including SUBSCRIPTION_ID and PROTOCOL. Google Play
        // Services' SMS User Consent silently filters out rows that are missing
        // these fields on dual-SIM phones (treats them as untrusted).
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

        val first = messages.first()
        val sender = first.displayOriginatingAddress ?: "UNKNOWN"
        val timestamp = first.timestampMillis
        val body = messages.joinToString(separator = "") { it.displayMessageBody ?: "" }
        val serviceCenter = first.serviceCenterAddress
        val protocol = runCatching { first.protocolIdentifier }.getOrNull()
        val subscriptionId = extractSubscriptionId(intent, first)

        AppLog.d(
            TAG,
            "Received SMS from $sender, length=${body.length}, " +
                "subId=$subscriptionId, protocol=$protocol, sc=$serviceCenter"
        )

        writeToSystemSmsProvider(
            context = context.applicationContext,
            sender = sender,
            body = body,
            timestamp = timestamp,
            serviceCenter = serviceCenter,
            protocol = protocol,
            subscriptionId = subscriptionId
        )

        // === STEP 2: Persist to our app DB, classify, notify (slower) — async.
        val pendingResult = goAsync()
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val threadId = ThreadUtils.calculateThreadId(sender)

                val messageEntity = MessageEntity(
                    sender = sender,
                    body = body,
                    ts = timestamp,
                    threadId = threadId,
                    type = 1,
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
     * Extract the SIM subscription id from the SMS_DELIVER intent. The platform
     * exposes it under several keys depending on the Android version & vendor;
     * the most common one is the literal "subscription" extra populated by
     * `InboundSmsHandler`. We try every known key and finally fall back to the
     * default outgoing SMS subscription, so that on single-SIM devices we still
     * get a valid id.
     */
    private fun extractSubscriptionId(intent: Intent, @Suppress("UNUSED_PARAMETER") first: SmsMessage): Int {
        val candidates = listOf(
            "subscription",
            SubscriptionManager.EXTRA_SUBSCRIPTION_INDEX,
            "android.telephony.extra.SUBSCRIPTION_INDEX"
        )
        for (key in candidates) {
            val v = intent.getIntExtra(key, INVALID_SUB_ID)
            if (v != INVALID_SUB_ID) return v
        }
        // Last resort: default SMS sub. Better than -1 because GPS treats -1
        // as "untrusted source" and silently filters the row out for User
        // Consent reads on dual-SIM phones.
        return runCatching {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP_MR1) {
                SubscriptionManager.getDefaultSmsSubscriptionId()
            } else {
                INVALID_SUB_ID
            }
        }.getOrDefault(INVALID_SUB_ID)
    }

    /**
     * Writes the incoming SMS to the system Telephony database (`content://sms`).
     *
     * IMPORTANT: We use `Telephony.Sms.CONTENT_URI` with an explicit `TYPE` field
     * (the AOSP Messaging app pattern) rather than `Telephony.Sms.Inbox.CONTENT_URI`.
     * The system provider then auto-populates `THREAD_ID` and other derived
     * columns the same way it does for AOSP Messaging / Google Messages /
     * Microsoft SMS Organizer — without this, OEM SMS providers on Xiaomi,
     * Oppo and OnePlus sometimes refuse the insert silently.
     */
    private fun writeToSystemSmsProvider(
        context: Context,
        sender: String,
        body: String,
        timestamp: Long,
        serviceCenter: String?,
        protocol: Int?,
        subscriptionId: Int
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
                if (serviceCenter != null) put(Telephony.Sms.SERVICE_CENTER, serviceCenter)
                if (protocol != null) put(Telephony.Sms.PROTOCOL, protocol)
                if (subscriptionId != INVALID_SUB_ID) {
                    put(Telephony.Sms.SUBSCRIPTION_ID, subscriptionId)
                }
            }

            val uri = context.contentResolver.insert(Telephony.Sms.CONTENT_URI, values)
            if (uri != null) {
                AppLog.d(TAG, "Wrote SMS to system provider at $uri (subId=$subscriptionId)")
            } else {
                AppLog.w(
                    TAG,
                    "System SMS provider returned null URI — are we really the default SMS handler? OTP autofill will not work."
                )
            }
        } catch (t: Throwable) {
            AppLog.e(TAG, "Failed to write SMS to system provider", t)
        }
    }

    companion object {
        private const val TAG = "SmsDeliverReceiver"
        private const val INVALID_SUB_ID = -1
    }
}
