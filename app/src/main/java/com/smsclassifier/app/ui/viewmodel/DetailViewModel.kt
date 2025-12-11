package com.smsclassifier.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import android.content.Context
import com.smsclassifier.app.classification.FeatureExtractor
import com.smsclassifier.app.classification.ServerClassifier
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.FeedbackEntity
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.data.MisclassificationLogEntity
import com.smsclassifier.app.work.ClassificationWorker
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

    fun reportAsWrong(correction: String) {
        viewModelScope.launch {
            val msg = _message.value ?: return@launch
            database.feedbackDao().insert(
                FeedbackEntity(
                    messageId = msg.id,
                    originalIsOtp = msg.isOtp,
                    originalOtpIntent = msg.otpIntent,
                    originalIsPhishing = msg.isPhishing,
                    originalPhishScore = msg.phishScore,
                    userCorrection = correction
                )
            )
            database.messageDao().markReviewed(msg.id)
            database.misclassificationLogDao().insert(
                MisclassificationLogEntity(
                    messageId = msg.id,
                    sender = msg.sender,
                    body = msg.body,
                    predictedIsOtp = msg.isOtp,
                    predictedOtpIntent = msg.otpIntent,
                    predictedIsPhishing = msg.isPhishing,
                    userNote = correction.ifBlank { null }
                )
            )
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
}

