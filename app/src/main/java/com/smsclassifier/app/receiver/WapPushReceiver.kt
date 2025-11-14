package com.smsclassifier.app.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

class WapPushReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        Log.d(TAG, "Received WAP push intent: ${intent.action}")
        // No-op for now. Implement MMS handling here if needed.
    }

    companion object {
        private const val TAG = "WapPushReceiver"
    }
}
