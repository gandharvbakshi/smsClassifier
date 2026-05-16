package com.smsclassifier.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Inbox
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
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
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.paging.LoadState
import androidx.paging.compose.collectAsLazyPagingItems
import androidx.paging.compose.itemKey
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.ui.components.ConversationItem
import com.smsclassifier.app.ui.components.FilterChips
import com.smsclassifier.app.ui.components.MessageItem
import com.smsclassifier.app.ui.components.OtpStrip
import com.smsclassifier.app.ui.viewmodel.FilterType
import com.smsclassifier.app.ui.viewmodel.InboxViewModel
import com.smsclassifier.app.ui.viewmodel.ViewMode

data class InboxEntitlementUi(
    val showTrialWelcome: Boolean = false,
    val onTrialWelcomeDismiss: () -> Unit = {},
    val showTrialEnding: Boolean = false,
    val trialDaysRemaining: Int = 0,
    val formattedPrice: String? = null,
    val onTrialEndingBuy: () -> Unit = {},
    val onTrialEndingDismiss: () -> Unit = {},
    val showUnlockPro: Boolean = false,
    val onUnlockPro: () -> Unit = {},
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun InboxScreen(
    viewModel: InboxViewModel,
    onMessageClick: (Long) -> Unit,
    onThreadClick: (Long) -> Unit,
    onNewMessageClick: () -> Unit,
    onSetDefaultSms: () -> Unit,
    entitlementUi: InboxEntitlementUi = InboxEntitlementUi(),
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
            InboxEntitlementBanners(ui = entitlementUi)
            InboxHeader(
                searchQuery = searchQuery,
                onSearchChange = viewModel::setSearchQuery,
                viewMode = viewMode,
                onViewModeChange = viewModel::setViewMode,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 8.dp)
            )

            OtpStrip(
                messages = recentOtps,
                onCardClick = { id -> onMessageClick(id) }
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
                modifier = Modifier.fillMaxWidth()
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
                                    contentPadding = PaddingValues(top = 6.dp, bottom = 88.dp)
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
                                    contentPadding = PaddingValues(top = 4.dp, bottom = 88.dp)
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
                                        if (idx < pagingItems.itemCount - 1) {
                                            Divider(
                                                modifier = Modifier.padding(start = 66.dp),
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun InboxHeader(
    searchQuery: String,
    onSearchChange: (String) -> Unit,
    viewMode: ViewMode,
    onViewModeChange: (ViewMode) -> Unit,
    modifier: Modifier = Modifier
) {
    var menuExpanded by remember { mutableStateOf(false) }

    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Surface(
            modifier = Modifier
                .weight(1f)
                .height(44.dp),
            shape = RoundedCornerShape(22.dp),
            color = MaterialTheme.colorScheme.surfaceVariant
        ) {
            Row(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 14.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Search,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(20.dp)
                )
                BasicTextField(
                    value = searchQuery,
                    onValueChange = { next ->
                        if (searchQuery.isBlank() && next.isNotBlank()) {
                            AppContainer.telemetry.logSearchUsed("inbox")
                        }
                        onSearchChange(next)
                    },
                    singleLine = true,
                    textStyle = MaterialTheme.typography.bodyLarge.copy(
                        color = MaterialTheme.colorScheme.onSurface
                    ),
                    cursorBrush = SolidColor(MaterialTheme.colorScheme.primary),
                    modifier = Modifier.weight(1f),
                    decorationBox = { inner ->
                        if (searchQuery.isEmpty()) {
                            Text(
                                text = "Search messages",
                                style = MaterialTheme.typography.bodyLarge,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        inner()
                    }
                )
                if (searchQuery.isNotEmpty()) {
                    IconButton(
                        onClick = { onSearchChange("") },
                        modifier = Modifier.size(28.dp)
                    ) {
                        Icon(
                            Icons.Default.Close,
                            contentDescription = "Clear",
                            modifier = Modifier.size(18.dp)
                        )
                    }
                }
            }
        }

        Box {
            IconButton(onClick = { menuExpanded = true }) {
                Icon(Icons.Default.MoreVert, contentDescription = "More options")
            }
            DropdownMenu(
                expanded = menuExpanded,
                onDismissRequest = { menuExpanded = false }
            ) {
                DropdownMenuItem(
                    text = { Text("View as messages") },
                    onClick = {
                        AppContainer.telemetry.logCtaTap("inbox", "view_messages")
                        onViewModeChange(ViewMode.MESSAGES)
                        menuExpanded = false
                    },
                    trailingIcon = if (viewMode == ViewMode.MESSAGES) {
                        { Icon(Icons.Default.Check, contentDescription = null) }
                    } else null
                )
                DropdownMenuItem(
                    text = { Text("Group by sender (threads)") },
                    onClick = {
                        AppContainer.telemetry.logCtaTap("inbox", "view_threads")
                        onViewModeChange(ViewMode.THREADS)
                        menuExpanded = false
                    },
                    trailingIcon = if (viewMode == ViewMode.THREADS) {
                        { Icon(Icons.Default.Check, contentDescription = null) }
                    } else null
                )
            }
        }
    }
}

@Composable
private fun InboxEntitlementBanners(ui: InboxEntitlementUi) {
    val trialAvailable = !AppContainer.entitlementManager.hasTrialStarted()

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 6.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        if (ui.showTrialWelcome) {
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                )
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text(
                        text = "You've unlocked a 7-day free trial of Pro features — OTP classification, phishing detection, and intent.",
                        style = MaterialTheme.typography.bodyMedium
                    )
                    TextButton(onClick = ui.onTrialWelcomeDismiss) {
                        Text("Got it", fontWeight = FontWeight.SemiBold)
                    }
                }
            }
        }
        if (ui.showTrialEnding) {
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.secondaryContainer
                )
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text(
                        text = "Trial ends in ${ui.trialDaysRemaining} day(s). Keep Pro for ${ui.formattedPrice ?: "Play price"}.",
                        style = MaterialTheme.typography.bodyMedium
                    )
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.padding(top = 8.dp)
                    ) {
                        TextButton(onClick = ui.onTrialEndingBuy) { Text("Buy") }
                        TextButton(onClick = ui.onTrialEndingDismiss) { Text("Dismiss") }
                    }
                }
            }
        }
        if (ui.showUnlockPro) {
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant
                )
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text(
                        text = if (trialAvailable) {
                            "Cloud phishing risk is unavailable here. Start the 7-day Pro trial or unlock Pro for full cloud classification."
                        } else {
                            "Cloud phishing risk is unavailable here. Unlock Pro for full cloud classification."
                        },
                        style = MaterialTheme.typography.bodyMedium
                    )
                    TextButton(onClick = ui.onUnlockPro) {
                        Text(if (trialAvailable) "Start trial / Unlock Pro" else "Unlock Pro")
                    }
                }
            }
        }
    }
}
