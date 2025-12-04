package com.smsclassifier.app.ui.viewmodel

import android.content.Context
import android.content.Intent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smsclassifier.app.service.SmsSendService
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class ComposeViewModel : ViewModel() {
    
    private val _address = MutableStateFlow("")
    val address: StateFlow<String> = _address.asStateFlow()
    
    private val _message = MutableStateFlow("")
    val message: StateFlow<String> = _message.asStateFlow()
    
    private val _isSending = MutableStateFlow(false)
    val isSending: StateFlow<Boolean> = _isSending.asStateFlow()
    
    fun setAddress(address: String) {
        _address.value = address
    }
    
    fun setMessage(message: String) {
        _message.value = message
    }
    
    fun sendMessage(context: Context, onSuccess: () -> Unit) {
        val addressValue = _address.value.trim()
        val messageValue = _message.value.trim()
        
        if (addressValue.isEmpty() || messageValue.isEmpty()) {
            return
        }
        
        viewModelScope.launch {
            _isSending.value = true
            try {
                val intent = Intent(context, SmsSendService::class.java).apply {
                    putExtra("android.intent.extra.PHONE_NUMBER", addressValue)
                    putExtra("android.intent.extra.TEXT", messageValue)
                }
                context.startService(intent)
                
                // Clear message after sending
                _message.value = ""
                onSuccess()
            } catch (e: Exception) {
                // Handle error
            } finally {
                _isSending.value = false
            }
        }
    }
    
    fun getCharacterCount(): Int {
        return _message.value.length
    }
    
    fun getMessageCount(): Int {
        // SMS are limited to 160 characters per message
        // Long messages are split into multiple parts
        val length = _message.value.length
        return if (length <= 160) 1 else (length / 153) + 1 // 153 chars per part for multipart
    }
}

