package com.smsclassifier.app.ui.viewmodel

import android.app.role.RoleManager
import android.content.Context
import android.os.Build
import android.provider.Telephony
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.MessageDao
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.data.ThreadInfo
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.launch

class ConversationListViewModel(
    private val database: AppDatabase,
    private val context: Context? = null
) : ViewModel() {
    
    private val _conversations = MutableStateFlow<List<ThreadInfo>>(emptyList())
    val conversations: StateFlow<List<ThreadInfo>> = _conversations.asStateFlow()
    
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()
    
    private val _isDefaultSmsHandler = MutableStateFlow<Boolean?>(null)
    val isDefaultSmsHandler: StateFlow<Boolean?> = _isDefaultSmsHandler.asStateFlow()
    
    init {
        loadConversations()
        checkDefaultSmsStatus()
    }
    
    private fun checkDefaultSmsStatus() {
        if (context != null) {
            val isDefault = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val roleManager = context.getSystemService(RoleManager::class.java)
                roleManager?.isRoleHeld(RoleManager.ROLE_SMS) ?: false
            } else {
                Telephony.Sms.getDefaultSmsPackage(context) == context.packageName
            }
            _isDefaultSmsHandler.value = isDefault
        }
    }
    
    fun loadConversations() {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                val dao = database.messageDao()
                val threadIds = dao.getAllThreadIds()
                
                val threadInfos = threadIds.mapNotNull { threadId ->
                    val messages = dao.getMessagesByThread(threadId)
                    if (messages.isEmpty()) return@mapNotNull null
                    
                    val latestMessage = messages.maxByOrNull { it.ts } ?: return@mapNotNull null
                    val unreadCount = dao.getUnreadCountForThread(threadId)
                    
                    ThreadInfo(
                        threadId = threadId,
                        address = latestMessage.sender,
                        snippet = latestMessage.body.take(50) + if (latestMessage.body.length > 50) "..." else "",
                        lastMessageTime = latestMessage.ts,
                        messageCount = messages.size,
                        unreadCount = unreadCount,
                        latestMessage = latestMessage
                    )
                }.sortedByDescending { it.lastMessageTime }
                
                _conversations.value = threadInfos
            } catch (e: Exception) {
                // Handle error
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    fun deleteThread(threadId: Long) {
        viewModelScope.launch {
            try {
                database.messageDao().deleteThread(threadId)
                loadConversations()
            } catch (e: Exception) {
                // Handle error
            }
        }
    }
    
    fun refresh() {
        loadConversations()
    }
}

