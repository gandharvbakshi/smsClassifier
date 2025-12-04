package com.smsclassifier.app

import android.app.Application
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.util.NotificationHelper
import com.smsclassifier.app.work.ClassificationWorker

class SMSClassifierApplication : Application() {
    private lateinit var database: AppDatabase

    override fun onCreate() {
        super.onCreate()
        database = AppDatabase.getDatabase(this)
        
        // Initialize notification channel early at app startup
        NotificationHelper.createNotificationChannel(this)
        
        ClassificationWorker.enqueue(this)
    }
}

