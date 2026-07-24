package com.smsclassifier.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.PagingData
import androidx.paging.cachedIn
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.data.ThreadInfo
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.launch

enum class FilterType {
    OTP, PHISHING, NEEDS_REVIEW, GENERAL, ALL
}

enum class ViewMode {
    THREADS, MESSAGES
}

@OptIn(ExperimentalCoroutinesApi::class)
class InboxViewModel(private val database: AppDatabase) : ViewModel() {
    private val _filter = MutableStateFlow(FilterType.ALL)
    val filter: StateFlow<FilterType> = _filter.asStateFlow()

    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    private val _conversations = MutableStateFlow<List<ThreadInfo>>(emptyList())
    val conversations: StateFlow<List<ThreadInfo>> = _conversations.asStateFlow()
    
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _viewMode = MutableStateFlow(ViewMode.MESSAGES)
    val viewMode: StateFlow<ViewMode> = _viewMode.asStateFlow()

    private var lastAutoMessageId: Long? = null
    private var conversationsLoadJob: Job? = null
    private var countsLoadJob: Job? = null

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
    val classifiedMessageCount = database.messageDao().getClassifiedCount()
    val otpMessageCount = database.messageDao().getOtpCount()
    val phishingMessageCount = database.messageDao().getPhishingCount()
    val needsReviewMessageCount = database.messageDao().getNeedsReviewCount()
    val generalMessageCount = database.messageDao().getGeneralCount()
    
    // Thread counts back the "By person" view; message counts back "By message".
    private val _totalThreadCount = MutableStateFlow(0)
    val totalThreadCount: StateFlow<Int> = _totalThreadCount.asStateFlow()

    private val _otpCount = MutableStateFlow(0)
    val otpCount: StateFlow<Int> = _otpCount.asStateFlow()
    
    private val _phishingCount = MutableStateFlow(0)
    val phishingCount: StateFlow<Int> = _phishingCount.asStateFlow()
    
    private val _needsReviewCount = MutableStateFlow(0)
    val needsReviewCount: StateFlow<Int> = _needsReviewCount.asStateFlow()
    
    private val _generalCount = MutableStateFlow(0)
    val generalCount: StateFlow<Int> = _generalCount.asStateFlow()

    init {
        refreshCounts()

        viewModelScope.launch {
            database.messageDao().getLatestMessage().collect { latest ->
                latest?.let { message ->
                    if (message.id != lastAutoMessageId) {
                        lastAutoMessageId = message.id
                        refreshCounts()
                        if (_viewMode.value == ViewMode.THREADS) {
                            loadConversations()
                        }
                    }
                }
            }
        }
    }

    fun setViewMode(mode: ViewMode) {
        if (_viewMode.value != mode) {
            AppContainer.telemetry.logEvent(
                "inbox_view_mode_changed",
                mapOf("mode" to mode.name.lowercase())
            )
        }
        _viewMode.value = mode
        if (mode == ViewMode.THREADS && _conversations.value.isEmpty()) {
            loadConversations()
        }
    }

    fun loadConversations() {
        if (conversationsLoadJob?.isActive == true) return
        conversationsLoadJob = viewModelScope.launch {
            _isLoading.value = true
            try {
                val dao = database.messageDao()
                val threadIds = dao.getAllThreadIds()
                
                updateCounts()
                
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
        refreshCounts()
        if (_viewMode.value == ViewMode.THREADS) {
            loadConversations()
        }
    }

    fun resetToAll() {
        _searchQuery.value = ""
        setFilter(FilterType.ALL)
    }

    fun setSearchQuery(query: String) {
        _searchQuery.value = query
    }

    private fun refreshCounts() {
        if (countsLoadJob?.isActive == true) return
        countsLoadJob = viewModelScope.launch {
            updateCounts()
        }
    }

    private suspend fun updateCounts() {
        val dao = database.messageDao()
        _totalThreadCount.value = dao.getTotalThreadCount()
        _otpCount.value = dao.getOtpThreadCount()
        _phishingCount.value = dao.getPhishingThreadCount()
        _needsReviewCount.value = dao.getNeedsReviewThreadCount()
        _generalCount.value = dao.getGeneralThreadCount()
    }
}
