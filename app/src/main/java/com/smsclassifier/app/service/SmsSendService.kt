package com.smsclassifier.app.service

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.telephony.SmsManager
import android.util.Log

class SmsSendService : Service() {
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        try {
            val address = intent?.getStringExtra(EXTRA_PHONE_NUMBER)
                ?: intent?.data?.schemeSpecificPart
            val message = intent?.getStringExtra(EXTRA_SMS_MESSAGE_BODY)
                ?: intent?.getStringExtra(Intent.EXTRA_TEXT)

            if (!address.isNullOrBlank() && !message.isNullOrBlank()) {
                val smsManager = SmsManager.getDefault()
                smsManager.sendTextMessage(address, null, message, null, null)
                Log.d(TAG, "Sent SMS to $address")
            } else {
                Log.w(TAG, "Missing address or message in SmsSendService")
            }
        } catch (t: Throwable) {
            Log.e(TAG, "Failed to send SMS", t)
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
    }
}
