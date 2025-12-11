package com.smsclassifier.app.util

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.smsclassifier.app.data.AppDatabase
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class MarkAsReadReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val threadId = intent.getLongExtra("threadId", -1L)
        
        if (threadId != -1L) {
            AppLog.d(TAG, "Marking thread $threadId as read")
            
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val database = AppDatabase.getDatabase(context.applicationContext)
                    database.messageDao().markThreadAsRead(threadId)
                    
                    // Cancel notification for this thread
                    NotificationHelper.cancelNotification(context, threadId.toInt())
                    
                    AppLog.d(TAG, "Thread $threadId marked as read")
                } catch (e: Exception) {
                    AppLog.e(TAG, "Failed to mark thread as read", e)
                }
            }
        }
    }
    
    companion object {
        private const val TAG = "MarkAsReadReceiver"
    }
}

