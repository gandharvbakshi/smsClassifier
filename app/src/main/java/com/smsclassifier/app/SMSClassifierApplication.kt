package com.smsclassifier.app

import android.app.Application
import com.google.firebase.installations.FirebaseInstallations
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.SettingsRepository
import com.smsclassifier.app.util.AppLog
import com.smsclassifier.app.util.NotificationHelper
import com.smsclassifier.app.util.ThreadUtils
import com.smsclassifier.app.work.ClassificationWorker
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

class SMSClassifierApplication : Application() {
    private lateinit var database: AppDatabase

    override fun onCreate() {
        super.onCreate()
        AppContainer.init(this)

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val lp = getSharedPreferences("telemetry_launch", MODE_PRIVATE)
                if (!lp.contains("first_open_at_ms")) {
                    lp.edit().putLong("first_open_at_ms", System.currentTimeMillis()).apply()
                }
            } catch (_: Exception) { }
        }

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val settingsPrefs = getSharedPreferences("sms_classifier_settings", MODE_PRIVATE)
                if (settingsPrefs.contains("install_id_anonymous_v1")) {
                    AppContainer.consentManager.markOnboardingConsentSeen()
                }
            } catch (e: Exception) {
                AppLog.w("SMSClassifierApplication", "Consent migration: ${e.message}")
            }
        }

        database = AppDatabase.getDatabase(this)

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val fid = FirebaseInstallations.getInstance().id.await()
                SettingsRepository(this@SMSClassifierApplication).applyFirebaseInstallId(fid)
            } catch (e: Exception) {
                AppLog.e("SMSClassifierApplication", "Firebase Installations id failed: ${e.message}", e)
            }
        }

        // Initialize notification channel early at app startup
        NotificationHelper.createNotificationChannel(this)

        ClassificationWorker.enqueue(this)

        AppContainer.billingRepository.startConnection()

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
