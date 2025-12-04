package com.smsclassifier.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.PagingData
import androidx.paging.cachedIn
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.data.ThreadInfo
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.launch

enum class FilterType {
    OTP, PHISHING, NEEDS_REVIEW, GENERAL, ALL
}

class InboxViewModel(private val database: AppDatabase) : ViewModel() {
    private val _filter = MutableStateFlow(FilterType.ALL)
    val filter: StateFlow<FilterType> = _filter.asStateFlow()

    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    private val _conversations = MutableStateFlow<List<ThreadInfo>>(emptyList())
    val conversations: StateFlow<List<ThreadInfo>> = _conversations.asStateFlow()
    
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private var lastAutoMessageId: Long? = null

    val messages: Flow<PagingData<MessageEntity>> =
        _filter.flatMapLatest { filterType ->
            Pager(
                config = PagingConfig(pageSize = 20, enablePlaceholders = false),
                pagingSourceFactory = {
                    when (filterType) {
                        FilterType.ALL -> database.messageDao().getAllPaged()
                        FilterType.OTP -> database.messageDao().getOtpPaged()
                        FilterType.PHISHING -> database.messageDao().getPhishingPaged()
                        FilterType.NEEDS_REVIEW -> database.messageDao().getNeedsReviewPaged()
                        FilterType.GENERAL -> database.messageDao().getGeneralPaged()
                    }
                }
            ).flow
        }.cachedIn(viewModelScope)

    val totalCount = database.messageDao().getTotalCount()
    
    // Count threads instead of individual messages
    private val _otpCount = MutableStateFlow(0)
    val otpCount: StateFlow<Int> = _otpCount.asStateFlow()
    
    private val _phishingCount = MutableStateFlow(0)
    val phishingCount: StateFlow<Int> = _phishingCount.asStateFlow()
    
    private val _needsReviewCount = MutableStateFlow(0)
    val needsReviewCount: StateFlow<Int> = _needsReviewCount.asStateFlow()
    
    private val _generalCount = MutableStateFlow(0)
    val generalCount: StateFlow<Int> = _generalCount.asStateFlow()

    init {
        // Load existing conversations immediately when ViewModel is created
        loadConversations()
        
        // Observe for new messages and refresh conversations when they arrive
        viewModelScope.launch {
            database.messageDao().getLatestMessage().collect { latest ->
                latest?.let { message ->
                    if (message.id != lastAutoMessageId) {
                        lastAutoMessageId = message.id
                        _filter.value = determineFilterForMessage(message)
                        loadConversations() // Refresh conversations when new message arrives
                    }
                }
            }
        }
    }

    fun loadConversations() {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                val dao = database.messageDao()
                val threadIds = dao.getAllThreadIds()
                
                // Update thread counts
                _otpCount.value = dao.getOtpThreadCount()
                _phishingCount.value = dao.getPhishingThreadCount()
                _needsReviewCount.value = dao.getNeedsReviewThreadCount()
                _generalCount.value = dao.getGeneralThreadCount()
                
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
                
                // Filter conversations based on selected filter
                // Check all messages in thread, not just latest
                val filtered = when (_filter.value) {
                    FilterType.ALL -> threadInfos
                    FilterType.OTP -> {
                        threadInfos.filter { threadInfo ->
                            val threadMessages = dao.getMessagesByThread(threadInfo.threadId)
                            threadMessages.any { it.isOtp == true }
                        }
                    }
                    FilterType.PHISHING -> {
                        threadInfos.filter { threadInfo ->
                            val threadMessages = dao.getMessagesByThread(threadInfo.threadId)
                            threadMessages.any { it.isPhishing == true }
                        }
                    }
                    FilterType.NEEDS_REVIEW -> {
                        threadInfos.filter { threadInfo ->
                            val threadMessages = dao.getMessagesByThread(threadInfo.threadId)
                            threadMessages.any { msg ->
                                !msg.reviewed && (msg.isPhishing == null || msg.phishScore == null)
                            }
                        }
                    }
                    FilterType.GENERAL -> {
                        threadInfos.filter { threadInfo ->
                            val threadMessages = dao.getMessagesByThread(threadInfo.threadId)
                            threadMessages.all { msg ->
                                (msg.isOtp == null || msg.isOtp == false) && 
                                (msg.isPhishing == null || msg.isPhishing == false)
                            }
                        }
                    }
                }
                
                _conversations.value = filtered
            } catch (e: Exception) {
                // Handle error
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun setFilter(filter: FilterType) {
        _filter.value = filter
        loadConversations() // Reload with new filter
    }

    fun setSearchQuery(query: String) {
        _searchQuery.value = query
    }

    private fun determineFilterForMessage(message: MessageEntity): FilterType {
        return when {
            message.isPhishing == true -> FilterType.PHISHING
            message.isOtp == true -> FilterType.OTP
            !message.reviewed -> FilterType.NEEDS_REVIEW
            else -> FilterType.ALL
        }
    }
}

