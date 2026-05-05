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

class OtpInboxViewModel(private val database: AppDatabase) : ViewModel() {

    val messages: Flow<PagingData<MessageEntity>> =
        Pager(
            config = PagingConfig(pageSize = 20, enablePlaceholders = false),
            pagingSourceFactory = { database.messageDao().getOtpPaged() }
        ).flow.cachedIn(viewModelScope)
}
