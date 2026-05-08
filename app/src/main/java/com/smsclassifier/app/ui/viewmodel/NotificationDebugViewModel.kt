package com.smsclassifier.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.NotificationDebugLogEntity
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class NotificationDebugViewModel(database: AppDatabase) : ViewModel() {
    private val dao = database.notificationDebugLogDao()

    val logs: StateFlow<List<NotificationDebugLogEntity>> = dao.getRecent().stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5_000),
        initialValue = emptyList()
    )

    fun clear() {
        viewModelScope.launch { dao.clear() }
    }
}
