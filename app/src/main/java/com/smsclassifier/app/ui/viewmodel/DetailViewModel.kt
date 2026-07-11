package com.smsclassifier.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import android.content.Context
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.classification.ServerClassifier
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.FeedbackEntity
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.data.MisclassificationLogEntity
import com.smsclassifier.app.data.SettingsRepository
import com.smsclassifier.app.util.AppLog
import com.smsclassifier.app.util.ClassificationUtils
import com.smsclassifier.app.work.ClassificationWorker
import com.smsclassifier.app.work.FeedbackUploadWorker
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class DetailViewModel(
    private val database: AppDatabase,
    private val context: Context? = null
) : ViewModel() {
    private val _message = MutableStateFlow<MessageEntity?>(null)
    val message: StateFlow<MessageEntity?> = _message.asStateFlow()
    
    private val _isRetrying = MutableStateFlow(false)
    val isRetrying: StateFlow<Boolean> = _isRetrying.asStateFlow()

    fun loadMessage(id: Long) {
        viewModelScope.launch {
            _message.value = database.messageDao().getById(id)
        }
    }

    fun reportAsWrong(
        correctionKind: String,
        correctionText: String,
        correctedOtpIntent: String? = null,
        onComplete: (Boolean) -> Unit = {}
    ) {
        viewModelScope.launch {
            var saved = false
            try {
                val msg = _message.value ?: return@launch
                val telemetryParams = buildMap<String, Any?> {
                    put("correction_kind", correctionKind)
                    correctedOtpIntent?.let { put("corrected_otp_intent", it) }
                }
                AppContainer.telemetry.logEvent(
                    "feedback_submitted",
                    telemetryParams
                )
                database.feedbackDao().insert(
                    FeedbackEntity(
                        messageId = msg.id,
                        originalIsOtp = msg.isOtp,
                        originalOtpIntent = msg.otpIntent,
                        originalIsPhishing = msg.isPhishing,
                        originalPhishScore = msg.phishScore,
                        userCorrection = correctionText
                    )
                )
                database.misclassificationLogDao().insert(
                    MisclassificationLogEntity(
                        messageId = msg.id,
                        sender = msg.sender,
                        body = msg.body,
                        predictedIsOtp = msg.isOtp,
                        predictedOtpIntent = msg.otpIntent,
                        correctedOtpIntent = correctedOtpIntent,
                        predictedIsPhishing = msg.isPhishing,
                        predictedPhishScore = msg.phishScore,
                        feedbackKind = correctionKind,
                        userNote = correctionText.ifBlank { null }
                    )
                )
                val correctedMessage = ClassificationUtils.applyUserCorrection(
                    msg,
                    correctionKind,
                    correctedOtpIntent
                )
                database.messageDao().update(correctedMessage)
                _message.value = database.messageDao().getById(msg.id) ?: correctedMessage
                saved = true
                context?.applicationContext?.let { appCtx ->
                    if (SettingsRepository(appCtx).feedbackUploadEnabled) {
                        FeedbackUploadWorker.enqueue(appCtx)
                    }
                }
            } catch (e: Exception) {
                AppLog.e(TAG, "Failed to save feedback report", e)
            } finally {
                onComplete(saved)
            }
        }
    }
    
    fun retryClassification() {
        viewModelScope.launch {
            val msg = _message.value ?: return@launch
            if (context == null) return@launch
            
            _isRetrying.value = true
            try {
                // Mark as unclassified to trigger re-classification
                val unclassifiedMessage = msg.copy(
                    isOtp = null,
                    otpIntent = null,
                    isPhishing = null,
                    phishScore = null,
                    reasonsJson = null
                )
                database.messageDao().update(unclassifiedMessage)
                
                // Trigger classification worker
                ClassificationWorker.enqueue(context)
                
                // Reload message after a short delay
                kotlinx.coroutines.delay(2000)
                _message.value = database.messageDao().getById(msg.id)
            } catch (e: Exception) {
                // Handle error
            } finally {
                _isRetrying.value = false
            }
        }
    }

    fun deleteMessage(onComplete: () -> Unit = {}) {
        viewModelScope.launch {
            try {
                val msg = _message.value ?: return@launch
                database.messageDao().delete(msg.id)
                _message.value = null
                onComplete()
            } catch (e: Exception) {
                AppLog.e(TAG, "Failed to delete message", e)
            }
        }
    }

    companion object {
        private const val TAG = "DetailViewModel"
    }
}

