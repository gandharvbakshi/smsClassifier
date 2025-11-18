package com.smsclassifier.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.PagingData
import androidx.paging.cachedIn
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.MessageEntity
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
    val otpCount = database.messageDao().getOtpCount()
    val phishingCount = database.messageDao().getPhishingCount()
    val needsReviewCount = database.messageDao().getNeedsReviewCount()
    val generalCount = database.messageDao().getGeneralCount()

    init {
        viewModelScope.launch {
            database.messageDao().getLatestMessage().collect { latest ->
                latest?.let { message ->
                    if (message.id != lastAutoMessageId) {
                        lastAutoMessageId = message.id
                        _filter.value = determineFilterForMessage(message)
                    }
                }
            }
        }
    }

    fun setFilter(filter: FilterType) {
        _filter.value = filter
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

