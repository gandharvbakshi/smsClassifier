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
import com.smsclassifier.app.util.ContactHelper
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.launch
import java.util.concurrent.ConcurrentHashMap
import android.net.Uri

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
    
    // Cache for contact names to avoid repeated queries
    private val contactNameCache = ConcurrentHashMap<String, String?>()
    
    // Cache for contact photos
    private val contactPhotoCache = ConcurrentHashMap<String, android.net.Uri?>()
    
    // State for contact names (address -> name)
    private val _contactNames = MutableStateFlow<Map<String, String>>(emptyMap())
    val contactNames: StateFlow<Map<String, String>> = _contactNames.asStateFlow()
    
    // State for contact photos (address -> photo URI)
    private val _contactPhotos = MutableStateFlow<Map<String, android.net.Uri>>(emptyMap())
    val contactPhotos: StateFlow<Map<String, android.net.Uri>> = _contactPhotos.asStateFlow()
    
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
                
                // Load contact names and photos for all threads in parallel
                if (context != null) {
                    loadContactNames(threadInfos.map { it.address })
                    loadContactPhotos(threadInfos.map { it.address })
                }
            } catch (e: Exception) {
                // Handle error
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    private fun loadContactNames(phoneNumbers: List<String>) {
        if (context == null) return
        
        viewModelScope.launch {
            val nameMap = mutableMapOf<String, String>()
            
            // Load contact names in parallel for all phone numbers
            phoneNumbers.forEach { phoneNumber ->
                if (!contactNameCache.containsKey(phoneNumber)) {
                    val contactName = ContactHelper.getContactName(context, phoneNumber)
                    contactNameCache[phoneNumber] = contactName
                    contactName?.let { nameMap[phoneNumber] = it }
                } else {
                    contactNameCache[phoneNumber]?.let { nameMap[phoneNumber] = it }
                }
            }
            
            if (nameMap.isNotEmpty()) {
                _contactNames.value = _contactNames.value + nameMap
            }
        }
    }
    
    fun getContactName(phoneNumber: String): String? {
        return contactNameCache[phoneNumber] ?: _contactNames.value[phoneNumber]
    }
    
    private fun loadContactPhotos(phoneNumbers: List<String>) {
        if (context == null) return
        
        viewModelScope.launch {
            val photoMap = mutableMapOf<String, Uri>()
            
            // Load contact photos in parallel for all phone numbers
            phoneNumbers.forEach { phoneNumber ->
                if (!contactPhotoCache.containsKey(phoneNumber)) {
                    val photoUri = ContactHelper.getContactPhotoUri(context!!, phoneNumber)
                    contactPhotoCache[phoneNumber] = photoUri
                    photoUri?.let { photoMap[phoneNumber] = it }
                } else {
                    contactPhotoCache[phoneNumber]?.let { photoMap[phoneNumber] = it }
                }
            }
            
            if (photoMap.isNotEmpty()) {
                _contactPhotos.value = _contactPhotos.value + photoMap
            }
        }
    }
    
    fun getContactPhoto(phoneNumber: String): Uri? {
        return contactPhotoCache[phoneNumber] ?: _contactPhotos.value[phoneNumber]
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

