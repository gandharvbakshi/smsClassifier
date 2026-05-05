package com.smsclassifier.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Inbox
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DockedSearchBar
import androidx.compose.material3.Divider
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.paging.LoadState
import androidx.paging.compose.collectAsLazyPagingItems
import androidx.paging.compose.itemKey
import com.smsclassifier.app.ui.components.ConversationItem
import com.smsclassifier.app.ui.components.FilterChips
import com.smsclassifier.app.ui.components.MessageItem
import com.smsclassifier.app.ui.components.OtpStrip
import com.smsclassifier.app.ui.viewmodel.FilterType
import com.smsclassifier.app.ui.viewmodel.InboxViewModel
import com.smsclassifier.app.ui.viewmodel.ViewMode

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun InboxScreen(
    viewModel: InboxViewModel,
    onMessageClick: (Long) -> Unit,
    onThreadClick: (Long) -> Unit,
    onNewMessageClick: () -> Unit,
    onSetDefaultSms: () -> Unit,
    modifier: Modifier = Modifier
) {
    val conversations by viewModel.conversations.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val filter by viewModel.filter.collectAsState()
    val searchQuery by viewModel.searchQuery.collectAsState()
    val viewMode by viewModel.viewMode.collectAsState()
    val recentOtps by viewModel.recentOtps.collectAsState()

    val totalCount by viewModel.totalCount.collectAsState(initial = 0)
    val otpCount by viewModel.otpCount.collectAsState(initial = 0)
    val phishingCount by viewModel.phishingCount.collectAsState(initial = 0)
    val needsReviewCount by viewModel.needsReviewCount.collectAsState(initial = 0)
    val generalCount by viewModel.generalCount.collectAsState(initial = 0)

    var searchExpanded by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        viewModel.loadConversations()
    }

    val filteredConversations = remember(conversations, searchQuery) {
        if (searchQuery.isBlank()) conversations
        else conversations.filter {
            it.address.contains(searchQuery, ignoreCase = true) ||
                it.snippet.contains(searchQuery, ignoreCase = true)
        }
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        text = "Messages",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.SemiBold
                    )
                },
                actions = {},
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onNewMessageClick,
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
                icon = { Icon(Icons.Default.Add, contentDescription = "New message") },
                text = { Text("New", fontWeight = FontWeight.SemiBold) }
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(MaterialTheme.colorScheme.background)
        ) {
            DockedSearchBar(
                query = searchQuery,
                onQueryChange = viewModel::setSearchQuery,
                onSearch = { searchExpanded = false },
                active = searchExpanded,
                onActiveChange = { searchExpanded = it },
                placeholder = { Text("Search messages") },
                leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                trailingIcon = {
                    if (searchQuery.isNotEmpty()) {
                        IconButton(onClick = { viewModel.setSearchQuery("") }) {
                            Icon(Icons.Default.Close, contentDescription = "Clear")
                        }
                    }
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 4.dp)
            ) {
                // Suggestions slot unused for now
            }

            OtpStrip(
                messages = recentOtps,
                onCardClick = { id -> onMessageClick(id) }
            )

            SingleChoiceSegmentedButtonRow(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 4.dp)
            ) {
                SegmentedButton(
                    selected = viewMode == ViewMode.THREADS,
                    onClick = { viewModel.setViewMode(ViewMode.THREADS) },
                    shape = SegmentedButtonDefaults.itemShape(index = 0, count = 2)
                ) {
                    Text("Threads")
                }
                SegmentedButton(
                    selected = viewMode == ViewMode.MESSAGES,
                    onClick = { viewModel.setViewMode(ViewMode.MESSAGES) },
                    shape = SegmentedButtonDefaults.itemShape(index = 1, count = 2)
                ) {
                    Text("Messages")
                }
            }

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

            when (viewMode) {
                ViewMode.THREADS -> {
                    when {
                        isLoading && filteredConversations.isEmpty() -> {
                            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                CircularProgressIndicator()
                            }
                        }

                        filteredConversations.isEmpty() -> {
                            EmptyInboxState(
                                onSetDefaultSms = onSetDefaultSms,
                                modifier = Modifier
                                    .fillMaxSize()
                                    .padding(24.dp)
                            )
                        }

                        else -> {
                            Surface(
                                modifier = Modifier
                                    .fillMaxSize()
                                    .padding(horizontal = 12.dp, vertical = 8.dp),
                                shape = RoundedCornerShape(20.dp),
                                color = MaterialTheme.colorScheme.surface,
                                tonalElevation = 1.dp
                            ) {
                                LazyColumn(
                                    modifier = Modifier.fillMaxSize(),
                                    contentPadding = PaddingValues(vertical = 6.dp)
                                ) {
                                    itemsIndexed(
                                        items = filteredConversations,
                                        key = { _, c -> c.threadId }
                                    ) { index, conversation ->
                                        ConversationItem(
                                            thread = conversation,
                                            onClick = { onThreadClick(conversation.threadId) },
                                            onLongClick = conversation.latestMessage?.let { message ->
                                                { onMessageClick(message.id) }
                                            },
                                            modifier = Modifier.fillMaxWidth()
                                        )
                                        if (index < filteredConversations.lastIndex) {
                                            Divider(
                                                modifier = Modifier.padding(start = 78.dp),
                                                color = MaterialTheme.colorScheme.outline.copy(alpha = 0.4f),
                                                thickness = 0.5.dp
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                ViewMode.MESSAGES -> {
                    val pagingItems = viewModel.messages.collectAsLazyPagingItems()
                    when {
                        pagingItems.loadState.refresh is LoadState.Loading &&
                            pagingItems.itemCount == 0 -> {
                            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                CircularProgressIndicator()
                            }
                        }

                        pagingItems.loadState.refresh is LoadState.NotLoading &&
                            pagingItems.itemCount == 0 -> {
                            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                Text(
                                    text = "No messages match this filter",
                                    style = MaterialTheme.typography.bodyLarge,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }

                        else -> {
                            Surface(
                                modifier = Modifier
                                    .fillMaxSize()
                                    .padding(horizontal = 12.dp, vertical = 8.dp),
                                shape = RoundedCornerShape(20.dp),
                                color = MaterialTheme.colorScheme.surface,
                                tonalElevation = 1.dp
                            ) {
                                LazyColumn(
                                    modifier = Modifier.fillMaxSize(),
                                    contentPadding = PaddingValues(vertical = 6.dp),
                                    verticalArrangement = Arrangement.spacedBy(8.dp)
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
                    }
                }
            }
        }
    }
}

@Composable
private fun EmptyInboxState(
    onSetDefaultSms: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(modifier = modifier, contentAlignment = Alignment.Center) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Box(
                modifier = Modifier
                    .size(64.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.primaryContainer),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Inbox,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(32.dp)
                )
            }
            Text(
                text = "No conversations yet",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                text = "Tap the New button below to start your first message.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            TextButton(onClick = onSetDefaultSms) {
                Text("Set as default SMS app")
            }
        }
    }
}
