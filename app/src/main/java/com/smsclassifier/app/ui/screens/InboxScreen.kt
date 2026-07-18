package com.smsclassifier.app.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
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
import androidx.compose.material3.Button
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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.paging.LoadState
import androidx.paging.compose.collectAsLazyPagingItems
import androidx.paging.compose.itemKey
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.R
import com.smsclassifier.app.entitlement.TrialNudgeMilestone
import com.smsclassifier.app.ui.components.ConversationItem
import com.smsclassifier.app.ui.components.FilterChips
import com.smsclassifier.app.ui.components.MessageItem
import com.smsclassifier.app.ui.components.PrimaryButton
import com.smsclassifier.app.ui.viewmodel.FilterType
import com.smsclassifier.app.ui.viewmodel.InboxViewModel
import com.smsclassifier.app.ui.viewmodel.ViewMode

data class InboxEntitlementUi(
    val showTrialWelcome: Boolean = false,
    val onTrialWelcomeDismiss: () -> Unit = {},
    val trialNudgeMilestone: TrialNudgeMilestone? = null,
    val trialDaysRemaining: Int = 0,
    val formattedPrice: String? = null,
    val onTrialNudgeShown: (TrialNudgeMilestone) -> Unit = {},
    val onTrialNudgeBuy: (TrialNudgeMilestone) -> Unit = {},
    val onTrialNudgeDismiss: (TrialNudgeMilestone) -> Unit = {},
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
    onOpenOtpTab: () -> Unit,
    onSetDefaultSms: () -> Unit,
    entitlementUi: InboxEntitlementUi = InboxEntitlementUi(),
    modifier: Modifier = Modifier
) {
    val conversations by viewModel.conversations.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val filter by viewModel.filter.collectAsState()
    val searchQuery by viewModel.searchQuery.collectAsState()
    val viewMode by viewModel.viewMode.collectAsState()

    val totalCount by viewModel.totalCount.collectAsState(initial = 0)
    val classifiedMessageCount by viewModel.classifiedMessageCount.collectAsState(initial = 0)
    val otpMessageCount by viewModel.otpMessageCount.collectAsState(initial = 0)
    val phishingMessageCount by viewModel.phishingMessageCount.collectAsState(initial = 0)
    val otpCount by viewModel.otpCount.collectAsState(initial = 0)
    val phishingCount by viewModel.phishingCount.collectAsState(initial = 0)
    val needsReviewCount by viewModel.needsReviewCount.collectAsState(initial = 0)
    val generalCount by viewModel.generalCount.collectAsState(initial = 0)

    LaunchedEffect(viewMode) {
        if (viewMode == ViewMode.THREADS) {
            viewModel.loadConversations()
        }
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
            InboxHeader(
                searchQuery = searchQuery,
                onSearchChange = viewModel::setSearchQuery,
                viewMode = viewMode,
                onViewModeChange = viewModel::setViewMode,
                modifier = Modifier
                    .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 8.dp)
            )

            FilterChips(
                selectedFilter = filter,
                onFilterSelected = { selected ->
                    if (selected == FilterType.OTP) onOpenOtpTab()
                    else viewModel.setFilter(selected)
                },
                counts = mapOf(
                    FilterType.OTP to otpCount,
                    FilterType.PHISHING to phishingCount,
                    FilterType.NEEDS_REVIEW to needsReviewCount,
                    FilterType.GENERAL to generalCount,
                    FilterType.ALL to totalCount
                ),
                modifier = Modifier.fillMaxWidth()
            )

            InboxEntitlementBanners(
                ui = entitlementUi,
                classifiedMessageCount = classifiedMessageCount,
                otpMessageCount = otpMessageCount,
                phishingMessageCount = phishingMessageCount
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
                    val refreshState = pagingItems.loadState.refresh
                    when {
                        refreshState is LoadState.Error && pagingItems.itemCount == 0 -> {
                            InboxLoadErrorState(
                                onRetry = { pagingItems.retry() },
                                modifier = Modifier
                                    .fillMaxSize()
                                    .padding(24.dp)
                            )
                        }

                        refreshState is LoadState.Loading && pagingItems.itemCount == 0 -> {
                            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                CircularProgressIndicator()
                            }
                        }

                        refreshState is LoadState.NotLoading && pagingItems.itemCount == 0 -> {
                            if (filter == FilterType.ALL && searchQuery.isBlank()) {
                                EmptyInboxState(
                                    onSetDefaultSms = onSetDefaultSms,
                                    modifier = Modifier
                                        .fillMaxSize()
                                        .padding(24.dp)
                                )
                            } else {
                                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                    Text(
                                        text = "No messages match this filter",
                                        style = MaterialTheme.typography.bodyLarge,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
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
private fun InboxLoadErrorState(
    onRetry: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(modifier = modifier, contentAlignment = Alignment.Center) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = stringResource(R.string.error_loading),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                text = "Try again. If this keeps happening, reopen the app.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            TextButton(onClick = onRetry) {
                Text("Retry")
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
                fontWeight = FontWeight.SemiBold,
                textAlign = TextAlign.Center
            )
            Text(
                text = "Make SMS Classifier your texting app to import texts and sort new messages.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth()
            )
            PrimaryButton(
                text = "Set as default SMS app",
                onClick = onSetDefaultSms
            )
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
                        modifier = Modifier.size(48.dp)
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
                    text = { Text("By message") },
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
                    text = { Text("By person") },
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
private fun InboxEntitlementBanners(
    ui: InboxEntitlementUi,
    classifiedMessageCount: Int,
    otpMessageCount: Int,
    phishingMessageCount: Int
) {
    val trialAvailable = !AppContainer.entitlementManager.hasTrialStarted()
    val trialLabel = AppContainer.entitlementManager.trialDurationLabel()

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 6.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        if (ui.showTrialWelcome) {
            EntitlementBannerCard(
                label = "Pro trial",
                body = "Pro is unlocked for $trialLabel: scam warnings, OTP purpose, and do-not-share alerts.",
                primaryText = "Got it",
                onPrimary = ui.onTrialWelcomeDismiss
            )
        }
        var displayedMilestone by remember { mutableStateOf<TrialNudgeMilestone?>(null) }
        LaunchedEffect(ui.trialNudgeMilestone) {
            val pendingMilestone = ui.trialNudgeMilestone
            if (displayedMilestone == null && pendingMilestone != null) {
                displayedMilestone = pendingMilestone
                ui.onTrialNudgeShown(pendingMilestone)
                AppContainer.telemetry.logTrialNudgeShown(pendingMilestone.daysRemaining)
            }
        }
        val milestone = displayedMilestone
        if (milestone != null) {
            val copy = trialNudgeCopy(
                milestone = milestone.daysRemaining,
                daysRemaining = ui.trialDaysRemaining.coerceIn(1, milestone.daysRemaining),
                classifiedMessageCount = classifiedMessageCount,
                otpMessageCount = otpMessageCount,
                phishingMessageCount = phishingMessageCount,
                formattedPrice = ui.formattedPrice
            )
            EntitlementBannerCard(
                label = copy.title,
                body = copy.body,
                primaryText = copy.primaryText,
                onPrimary = { ui.onTrialNudgeBuy(milestone) },
                secondaryText = if (milestone == TrialNudgeMilestone.DAY_1) null else "Not now",
                onSecondary = {
                    displayedMilestone = null
                    ui.onTrialNudgeDismiss(milestone)
                },
                showClose = milestone == TrialNudgeMilestone.DAY_1,
                onClose = { displayedMilestone = null }
            )
        }
        if (ui.showUnlockPro) {
            EntitlementBannerCard(
                label = "Pro needed",
                body = if (trialAvailable) {
                    "Scam warnings are unavailable here. Start a Pro trial ($trialLabel) or subscribe for scam warnings."
                } else {
                    "Scam warnings are unavailable here. Subscribe to Pro for scam warnings."
                },
                primaryText = if (trialAvailable) "Start trial" else "Subscribe",
                onPrimary = ui.onUnlockPro
            )
        }
    }
}

@Composable
private fun EntitlementBannerCard(
    label: String,
    body: String,
    primaryText: String? = null,
    onPrimary: () -> Unit = {},
    secondaryText: String? = null,
    onSecondary: () -> Unit = {},
    showClose: Boolean = false,
    onClose: () -> Unit = {}
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface,
            contentColor = MaterialTheme.colorScheme.onSurface
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 14.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = label,
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.weight(1f)
                )
                if (showClose) {
                    IconButton(onClick = onClose) {
                        Icon(Icons.Default.Close, contentDescription = "Close trial reminder")
                    }
                }
            }
            Text(
                text = body,
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface
            )
            if (primaryText != null || secondaryText != null) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.End),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    if (secondaryText != null) {
                        TextButton(onClick = onSecondary) {
                            Text(secondaryText)
                        }
                    }
                    if (primaryText != null) {
                        Button(
                            onClick = onPrimary,
                            modifier = Modifier.heightIn(min = 48.dp)
                        ) {
                            Text(primaryText, fontWeight = FontWeight.SemiBold)
                        }
                    }
                }
            }
        }
    }
}
