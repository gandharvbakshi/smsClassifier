package com.smsclassifier.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.FeedbackEntity
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.data.MisclassificationLogEntity
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class DetailViewModel(private val database: AppDatabase) : ViewModel() {
    private val _message = MutableStateFlow<MessageEntity?>(null)
    val message: StateFlow<MessageEntity?> = _message.asStateFlow()

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
}

