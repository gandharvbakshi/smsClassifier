package com.smsclassifier.app.ui.viewmodel

import android.content.Context
import android.content.Intent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.BulkSmsDeletion
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.service.SmsSendService
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class ThreadViewModel(
    private val database: AppDatabase
) : ViewModel() {
    internal val bulkDelete = BulkSmsDeletion(database)
    private var loadedThreadId: Long? = null
    private var observation: Job? = null
    
    private val _messages = MutableStateFlow<List<MessageEntity>>(emptyList())
    val messages: StateFlow<List<MessageEntity>> = _messages.asStateFlow()
    
    private val _threadAddress = MutableStateFlow<String>("")
    val threadAddress: StateFlow<String> = _threadAddress.asStateFlow()
    
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()
    
    fun loadThread(threadId: Long) {
        if (loadedThreadId == threadId && observation?.isActive == true) return
        observation?.cancel()
        loadedThreadId = threadId
        _messages.value = emptyList()
        _threadAddress.value = ""
        observation = viewModelScope.launch {
            _isLoading.value = true
            try {
                val dao = database.messageDao()
                dao.markThreadAsRead(threadId)
                dao.observeThread(threadId).collect { threadMessages ->
                    _messages.value = threadMessages
                    threadMessages.firstOrNull()?.let { _threadAddress.value = it.sender }
                    _isLoading.value = false
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                // Handle error
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    fun sendMessage(context: Context, threadId: Long, address: String, body: String): Boolean {
        val intent = Intent(context, SmsSendService::class.java).apply {
            putExtra("android.intent.extra.PHONE_NUMBER", address)
            putExtra("android.intent.extra.TEXT", body)
            putExtra(SmsSendService.EXTRA_LOCAL_THREAD_ID, threadId)
        }
        return runCatching { context.startService(intent) }.getOrNull() != null
    }
    
    fun refresh(threadId: Long) {
        loadThread(threadId)
    }
    
    fun deleteMessage(messageId: Long) {
        viewModelScope.launch {
            try {
                database.messageDao().delete(messageId)
            } catch (e: Exception) {
                // Handle error
            }
        }
    }
}

