package com.smsclassifier.app.ui.screens

import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.paging.compose.collectAsLazyPagingItems
import androidx.paging.compose.itemKey
import com.smsclassifier.app.ui.components.MessageItem
import com.smsclassifier.app.ui.viewmodel.FilterType
import com.smsclassifier.app.ui.viewmodel.InboxViewModel
import com.smsclassifier.app.ui.viewmodel.ViewMode

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FlaggedScreen(
    viewModel: InboxViewModel,
    onMessageClick: (Long) -> Unit,
    modifier: Modifier = Modifier
) {
    LaunchedEffect(Unit) {
        viewModel.setFilter(FilterType.PHISHING)
        viewModel.setViewMode(ViewMode.MESSAGES)
    }
    val pagingItems = viewModel.messages.collectAsLazyPagingItems()
    Scaffold(
        modifier = modifier,
        topBar = { TopAppBar(title = { Text("Flagged") }) }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 6.dp)
        ) {
            items(
                count = pagingItems.itemCount,
                key = pagingItems.itemKey { it.id }
            ) { idx ->
                val msg = pagingItems[idx] ?: return@items
                MessageItem(
                    message = msg,
                    onClick = { onMessageClick(msg.id) },
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }
    }
}
