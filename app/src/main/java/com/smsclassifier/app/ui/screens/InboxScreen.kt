package com.smsclassifier.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.paging.compose.LazyPagingItems
import androidx.paging.compose.collectAsLazyPagingItems
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.ui.components.MessageItem
import com.smsclassifier.app.ui.components.FilterChips
import com.smsclassifier.app.ui.theme.*
import com.smsclassifier.app.ui.viewmodel.FilterType
import com.smsclassifier.app.ui.viewmodel.InboxViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun InboxScreen(
    viewModel: InboxViewModel,
    onMessageClick: (Long) -> Unit,
    modifier: Modifier = Modifier
) {
    val messages = viewModel.messages.collectAsLazyPagingItems()
    val filter by viewModel.filter.collectAsState()
    val searchQuery by viewModel.searchQuery.collectAsState()
    
    val totalCount by viewModel.totalCount.collectAsState(initial = 0)
    val otpCount by viewModel.otpCount.collectAsState(initial = 0)
    val phishingCount by viewModel.phishingCount.collectAsState(initial = 0)
    val needsReviewCount by viewModel.needsReviewCount.collectAsState(initial = 0)
    val generalCount by viewModel.generalCount.collectAsState(initial = 0)

    Column(modifier = modifier.fillMaxSize()) {
        // Search bar
        SearchBar(
            query = searchQuery,
            onQueryChange = viewModel::setSearchQuery,
            modifier = Modifier.fillMaxWidth()
        )
        
        // Filter chips
        FilterChips(
            selectedFilter = filter,
            onFilterSelected = viewModel::setFilter,
            counts = mapOf(
                FilterType.OTP to otpCount,
                FilterType.PHISHING to phishingCount,
                FilterType.NEEDS_REVIEW to needsReviewCount,
                FilterType.GENERAL to generalCount,
                FilterType.ALL to totalCount
            ),
            modifier = Modifier.fillMaxWidth(),
            filterOrder = listOf(
                FilterType.OTP,
                FilterType.PHISHING,
                FilterType.NEEDS_REVIEW,
                FilterType.GENERAL,
                FilterType.ALL
            )
        )
        
        // Messages list
        when {
            messages.loadState.refresh is androidx.paging.LoadState.Loading -> {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            }
            messages.itemCount == 0 -> {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("No messages")
                }
            }
            else -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(messages.itemCount) { index ->
                        messages[index]?.let { message ->
                            MessageItem(
                                message = message,
                                onClick = { onMessageClick(message.id) },
                                modifier = Modifier.fillMaxWidth()
                            )
                        }
                    }
                    
                    if (messages.loadState.append is androidx.paging.LoadState.Loading) {
                        item {
                            CircularProgressIndicator(modifier = Modifier.fillMaxWidth())
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SearchBar(
    query: String,
    onQueryChange: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    OutlinedTextField(
        value = query,
        onValueChange = onQueryChange,
        modifier = modifier.padding(8.dp),
        leadingIcon = { Icon(Icons.Default.Search, contentDescription = "Search") },
        placeholder = { Text("Search messages...") },
        singleLine = true
    )
}

