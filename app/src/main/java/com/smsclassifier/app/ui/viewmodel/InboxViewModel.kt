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

enum class FilterType {
    ALL, OTP, PHISHING, NEEDS_REVIEW
}

class InboxViewModel(private val database: AppDatabase) : ViewModel() {
    private val _filter = MutableStateFlow(FilterType.ALL)
    val filter: StateFlow<FilterType> = _filter.asStateFlow()

    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    val messages: Flow<PagingData<MessageEntity>> = Pager(
        config = PagingConfig(pageSize = 20, enablePlaceholders = false),
        pagingSourceFactory = {
            when (_filter.value) {
                FilterType.ALL -> database.messageDao().getAllPaged()
                FilterType.OTP -> database.messageDao().getOtpPaged()
                FilterType.PHISHING -> database.messageDao().getPhishingPaged()
                FilterType.NEEDS_REVIEW -> database.messageDao().getNeedsReviewPaged()
            }
        }
    ).flow.cachedIn(viewModelScope)

    val totalCount = database.messageDao().getTotalCount()
    val otpCount = database.messageDao().getOtpCount()
    val phishingCount = database.messageDao().getPhishingCount()
    val needsReviewCount = database.messageDao().getNeedsReviewCount()

    fun setFilter(filter: FilterType) {
        _filter.value = filter
    }

    fun setSearchQuery(query: String) {
        _searchQuery.value = query
    }
}

