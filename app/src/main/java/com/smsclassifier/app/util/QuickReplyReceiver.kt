package com.smsclassifier.app.util

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.smsclassifier.app.MainActivity
import com.smsclassifier.app.util.AppLog

class QuickReplyReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val threadId = intent.getLongExtra("threadId", -1)
        val sender = intent.getStringExtra("sender") ?: ""
        
        AppLog.d(TAG, "Quick reply requested for thread $threadId from $sender")
        
        // Open app to thread view for reply
        val replyIntent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            putExtra("threadId", threadId)
            putExtra("openThread", true)
            putExtra("focusInput", true)
        }
        context.startActivity(replyIntent)
    }
    
    companion object {
        private const val TAG = "QuickReplyReceiver"
    }
}

