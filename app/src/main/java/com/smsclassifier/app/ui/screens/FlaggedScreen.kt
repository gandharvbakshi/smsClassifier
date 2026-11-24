package com.smsclassifier.app.ui.screens

import androidx.compose.foundation.layout.Column
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.paging.compose.collectAsLazyPagingItems
import androidx.paging.compose.itemKey
import com.smsclassifier.app.ui.components.BulkDeleteControls
import com.smsclassifier.app.ui.components.BulkDeleteMessageRow
import com.smsclassifier.app.ui.components.MessageItem
import com.smsclassifier.app.ui.components.rememberBulkDeleteSelection
import com.smsclassifier.app.ui.viewmodel.InboxViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FlaggedScreen(
    viewModel: InboxViewModel,
    onMessageClick: (Long) -> Unit,
    modifier: Modifier = Modifier
) {
    val pagingItems = viewModel.flaggedMessages.collectAsLazyPagingItems()
    val selection = rememberBulkDeleteSelection()
    Scaffold(
        modifier = modifier,
        topBar = {
            Column {
                TopAppBar(title = { Text("Flagged") })
                BulkDeleteControls(selection, viewModel.bulkDelete, canSelect = pagingItems.itemCount > 0)
            }
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(vertical = 6.dp)
        ) {
            items(
                count = pagingItems.itemCount,
                key = pagingItems.itemKey { it.id }
            ) { idx ->
                val msg = pagingItems[idx] ?: return@items
                if (selection.active) {
                    BulkDeleteMessageRow(selection, msg)
                } else MessageItem(
                    message = msg,
                    onClick = { onMessageClick(msg.id) },
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }
    }
}
