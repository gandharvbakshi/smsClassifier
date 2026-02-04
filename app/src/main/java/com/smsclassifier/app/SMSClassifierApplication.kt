package com.smsclassifier.app

import android.app.Application
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.util.AppLog
import com.smsclassifier.app.util.NotificationHelper
import com.smsclassifier.app.util.ThreadUtils
import com.smsclassifier.app.work.ClassificationWorker
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class SMSClassifierApplication : Application() {
    private lateinit var database: AppDatabase

    override fun onCreate() {
        super.onCreate()
        database = AppDatabase.getDatabase(this)
        
        // Initialize notification channel early at app startup
        NotificationHelper.createNotificationChannel(this)
        
        ClassificationWorker.enqueue(this)

        // Fix legacy thread IDs for alphanumeric senders (previously grouped into thread 0)
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val legacyThreadMessages = database.messageDao().getMessagesByThread(0)
                if (legacyThreadMessages.isNotEmpty()) {
                    legacyThreadMessages.forEach { message ->
                        val newThreadId = ThreadUtils.calculateThreadId(message.sender)
                        if (newThreadId != 0L && newThreadId != message.threadId) {
                            database.messageDao().update(message.copy(threadId = newThreadId))
                        }
                    }
                }
            } catch (e: Exception) {
                AppLog.e("SMSClassifierApplication", "Failed to rethread legacy messages", e)
            }
        }
    }
}

