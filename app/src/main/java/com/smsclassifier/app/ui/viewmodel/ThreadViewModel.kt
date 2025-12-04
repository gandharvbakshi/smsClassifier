package com.smsclassifier.app.ui.viewmodel

import android.content.Context
import android.content.Intent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.service.SmsSendService
import com.smsclassifier.app.util.ThreadUtils
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class ThreadViewModel(
    private val database: AppDatabase
) : ViewModel() {
    
    private val _messages = MutableStateFlow<List<MessageEntity>>(emptyList())
    val messages: StateFlow<List<MessageEntity>> = _messages.asStateFlow()
    
    private val _threadAddress = MutableStateFlow<String>("")
    val threadAddress: StateFlow<String> = _threadAddress.asStateFlow()
    
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()
    
    fun loadThread(threadId: Long) {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                val dao = database.messageDao()
                val threadMessages = dao.getMessagesByThread(threadId)
                _messages.value = threadMessages
                
                // Get the address from the first message
                threadMessages.firstOrNull()?.let {
                    _threadAddress.value = it.sender
                }
                
                // Mark thread as read
                dao.markThreadAsRead(threadId)
            } catch (e: Exception) {
                // Handle error
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    fun sendMessage(context: Context, address: String, body: String) {
        viewModelScope.launch {
            try {
                // Send via SmsSendService
                val intent = Intent(context, SmsSendService::class.java).apply {
                    putExtra("android.intent.extra.PHONE_NUMBER", address)
                    putExtra("android.intent.extra.TEXT", body)
                }
                context.startService(intent)
                
                // Refresh the thread after a short delay to show the new message
                kotlinx.coroutines.delay(500)
                val threadId = ThreadUtils.calculateThreadId(address)
                loadThread(threadId)
            } catch (e: Exception) {
                // Handle error
            }
        }
    }
    
    fun refresh(threadId: Long) {
        loadThread(threadId)
    }
    
    fun deleteMessage(messageId: Long) {
        viewModelScope.launch {
            try {
                database.messageDao().delete(messageId)
                // Reload thread to update UI
                val currentThreadId = _messages.value.firstOrNull()?.threadId
                if (currentThreadId != null) {
                    loadThread(currentThreadId)
                }
            } catch (e: Exception) {
                // Handle error
            }
        }
    }
}

