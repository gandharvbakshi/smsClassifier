package com.smsclassifier.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.paging.compose.collectAsLazyPagingItems
import com.smsclassifier.app.ui.components.FilterChips
import com.smsclassifier.app.ui.components.MessageItem
import com.smsclassifier.app.ui.components.ConversationItem
import com.smsclassifier.app.ui.viewmodel.FilterType
import com.smsclassifier.app.ui.viewmodel.InboxViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun InboxScreen(
    viewModel: InboxViewModel,
    onMessageClick: (Long) -> Unit,
    onThreadClick: (Long) -> Unit,
    onNewMessageClick: () -> Unit,
    onOpenLogs: () -> Unit,
    onOpenSettings: () -> Unit,
    modifier: Modifier = Modifier
) {
    val conversations by viewModel.conversations.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val filter by viewModel.filter.collectAsState()
    val searchQuery by viewModel.searchQuery.collectAsState()
    
    val totalCount by viewModel.totalCount.collectAsState(initial = 0)
    val otpCount by viewModel.otpCount.collectAsState(initial = 0)
    val phishingCount by viewModel.phishingCount.collectAsState(initial = 0)
    val needsReviewCount by viewModel.needsReviewCount.collectAsState(initial = 0)
    val generalCount by viewModel.generalCount.collectAsState(initial = 0)

    var menuExpanded by remember { mutableStateOf(false) }
    
    LaunchedEffect(Unit) {
        viewModel.loadConversations()
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopAppBar(
                title = { Text(text = "Inbox") },
                actions = {
                    IconButton(onClick = { menuExpanded = true }) {
                        Icon(Icons.Default.MoreVert, contentDescription = "More options")
                    }
                    DropdownMenu(
                        expanded = menuExpanded,
                        onDismissRequest = { menuExpanded = false }
                    ) {
                        DropdownMenuItem(
                            text = { Text("Misclassification logs") },
                            onClick = {
                                menuExpanded = false
                                onOpenLogs()
                            }
                        )
                        DropdownMenuItem(
                            text = { Text("Settings") },
                            onClick = {
                                menuExpanded = false
                                onOpenSettings()
                            }
                        )
                    }
                }
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = onNewMessageClick
            ) {
                Icon(
                    imageVector = Icons.Default.Add,
                    contentDescription = "New Message"
                )
            }
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            SearchBar(
                query = searchQuery,
                onQueryChange = viewModel::setSearchQuery,
                modifier = Modifier.fillMaxWidth()
            )

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

            when {
                isLoading && conversations.isEmpty() -> {
                    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator()
                    }
                }

                conversations.isEmpty() -> {
                    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Text("No conversations")
                            Text(
                                text = "Tap the + button to start a new message",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }

                else -> {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(8.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        items(conversations) { conversation ->
                            ConversationItem(
                                thread = conversation,
                                onClick = { onThreadClick(conversation.threadId) },
                                onLongClick = conversation.latestMessage?.let { message ->
                                    { onMessageClick(message.id) }
                                },
                                modifier = Modifier.fillMaxWidth()
                            )
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

