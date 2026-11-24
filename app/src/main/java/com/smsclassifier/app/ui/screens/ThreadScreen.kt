package com.smsclassifier.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.ReplyDraftsViewModel
import com.smsclassifier.app.ui.components.BulkDeleteControls
import com.smsclassifier.app.ui.components.BulkDeleteMessageRow
import com.smsclassifier.app.ui.components.ContactAvatar
import com.smsclassifier.app.ui.components.MessageBubble
import com.smsclassifier.app.ui.components.rememberBulkDeleteSelection
import com.smsclassifier.app.ui.viewmodel.ThreadViewModel
import com.smsclassifier.app.util.ReplyPolicy
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ThreadScreen(
    threadId: Long,
    viewModel: ThreadViewModel,
    onBack: () -> Unit,
    drafts: ReplyDraftsViewModel,
    replyRecipient: String? = null,
    focusReply: Boolean = false,
    onReplyFocused: () -> Unit = {},
    onMessageClick: (Long) -> Unit = {},
    modifier: Modifier = Modifier
) {
    val messages by viewModel.messages.collectAsState()
    val threadAddress by viewModel.threadAddress.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val selection = rememberBulkDeleteSelection(threadId)

    val recipient = replyRecipient ?: ReplyPolicy.recipient(threadAddress)
    val messageText = recipient?.let(drafts::get).orEmpty()
    val focusRequester = remember { FocusRequester() }
    val focusManager = LocalFocusManager.current
    val keyboard = LocalSoftwareKeyboardController.current
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    val replySnackbar = remember { SnackbarHostState() }

    LaunchedEffect(focusReply, recipient, selection.active) {
        if (focusReply && recipient != null && !selection.active) {
            withFrameNanos { }
            focusRequester.requestFocus()
            keyboard?.show()
            onReplyFocused()
        }
    }
    LaunchedEffect(selection.active) {
        if (selection.active) {
            focusManager.clearFocus()
            keyboard?.hide()
        }
    }

    val navigateBack = {
        focusManager.clearFocus()
        keyboard?.hide()
        onBack()
    }

    var firstLoad by remember { mutableStateOf(true) }
    var previousMessageCount by remember { mutableStateOf(0) }

    LaunchedEffect(threadId) {
        viewModel.loadThread(threadId)
        firstLoad = true
        previousMessageCount = 0
    }

    LaunchedEffect(messages.size) {
        val currentMessageCount = messages.size
        if (currentMessageCount > 0) {
            val visibleItems = listState.layoutInfo.visibleItemsInfo
            val lastVisibleIndex = visibleItems.lastOrNull()?.index ?: -1
            val isNearBottom = lastVisibleIndex >= currentMessageCount - 2
            val hasNewMessage = currentMessageCount > previousMessageCount

            if (firstLoad || (hasNewMessage && isNearBottom)) {
                scope.launch { listState.animateScrollToItem(currentMessageCount - 1) }
                firstLoad = false
            }
            previousMessageCount = currentMessageCount
        }
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        snackbarHost = { SnackbarHost(replySnackbar) },
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            Column {
                ThreadTopBar(
                    address = replyRecipient ?: threadAddress,
                    backContentDescription = if (selection.active) "Cancel selection" else "Back",
                    onBack = {
                        if (!selection.active) navigateBack()
                        else if (!selection.busy && selection.plan == null) selection.clear()
                    }
                )
                BulkDeleteControls(selection, viewModel.bulkDelete, canSelect = messages.isNotEmpty() && !isLoading)
            }
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .consumeWindowInsets(paddingValues)
                .imePadding()
                .background(MaterialTheme.colorScheme.background)
        ) {
            Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
                when {
                    isLoading && messages.isEmpty() -> {
                        CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                    }
                    messages.isEmpty() -> {
                        Text(
                            text = "No messages yet",
                            modifier = Modifier.align(Alignment.Center),
                            style = MaterialTheme.typography.bodyLarge,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    else -> {
                        LazyColumn(
                            state = listState,
                            modifier = Modifier.fillMaxSize(),
                            contentPadding = PaddingValues(vertical = 12.dp),
                            verticalArrangement = Arrangement.spacedBy(2.dp)
                        ) {
                            items(items = messages, key = { it.id }) { message ->
                                if (selection.active) {
                                    val sender = if (message.type == 1) message.sender else "You"
                                    BulkDeleteMessageRow(selection, message, title = sender)
                                } else MessageBubble(
                                    message = message,
                                    modifier = Modifier.fillMaxWidth(),
                                    onCopy = { /* handled in bubble */ },
                                    onDelete = { viewModel.deleteMessage(message.id) },
                                    onForward = null,
                                    onReport = { onMessageClick(message.id) }
                                )
                            }
                        }
                    }
                }
            }

            if (!selection.active && recipient != null) {
                ThreadInputBar(
                    text = messageText,
                    onTextChange = { drafts.update(recipient, it) },
                    focusRequester = focusRequester,
                    onSend = {
                        if (viewModel.sendMessage(context, threadId, recipient, messageText)) {
                            drafts.update(recipient, "")
                        } else {
                            scope.launch { replySnackbar.showSnackbar("Could not send the message. Try again.") }
                        }
                    }
                )
            } else if (!selection.active && threadAddress.isNotBlank()) {
                Text(
                    text = ReplyPolicy.UNAVAILABLE_MESSAGE,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ThreadTopBar(address: String, backContentDescription: String, onBack: () -> Unit) {
    TopAppBar(
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                ContactAvatar(name = address, size = 36.dp)
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Text(
                        text = address,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1
                    )
                }
            }
        },
        navigationIcon = {
            IconButton(onClick = onBack) {
                Icon(Icons.Default.ArrowBack, contentDescription = backContentDescription)
            }
        },
        colors = TopAppBarDefaults.topAppBarColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    )
}

@Composable
private fun ThreadInputBar(
    text: String,
    onTextChange: (String) -> Unit,
    focusRequester: FocusRequester,
    onSend: () -> Unit
) {
    Surface(
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 4.dp
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Surface(
                color = MaterialTheme.colorScheme.surfaceVariant,
                shape = RoundedCornerShape(28.dp),
                modifier = Modifier.weight(1f)
            ) {
                Box(
                    modifier = Modifier
                        .padding(horizontal = 16.dp, vertical = 12.dp)
                ) {
                    if (text.isEmpty()) {
                        Text(
                            text = "Type a message...",
                            modifier = Modifier.clearAndSetSemantics {},
                            style = MaterialTheme.typography.bodyLarge,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    BasicTextField(
                        value = text,
                        onValueChange = onTextChange,
                        textStyle = MaterialTheme.typography.bodyLarge.copy(
                            color = MaterialTheme.colorScheme.onSurface
                        ),
                        cursorBrush = SolidColor(MaterialTheme.colorScheme.primary),
                        modifier = Modifier
                            .fillMaxWidth()
                            .focusRequester(focusRequester)
                            .semantics { contentDescription = "Message" },
                        maxLines = 5
                    )
                }
            }

            Spacer(modifier = Modifier.width(10.dp))

            Box(
                modifier = Modifier
                    .size(48.dp)
                    .clip(CircleShape)
                    .background(
                        if (text.isNotBlank()) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.surfaceVariant
                    ),
                contentAlignment = Alignment.Center
            ) {
                IconButton(onClick = onSend, enabled = text.isNotBlank()) {
                    Icon(
                        imageVector = Icons.Default.Send,
                        contentDescription = "Send",
                        tint = if (text.isNotBlank()) MaterialTheme.colorScheme.onPrimary
                        else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}
