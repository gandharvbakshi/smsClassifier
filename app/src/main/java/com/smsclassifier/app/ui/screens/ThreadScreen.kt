package com.smsclassifier.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.ui.components.MessageBubble
import com.smsclassifier.app.ui.viewmodel.ThreadViewModel
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ThreadScreen(
    threadId: Long,
    viewModel: ThreadViewModel,
    onBack: () -> Unit,
    onMessageClick: (Long) -> Unit = {},
    modifier: Modifier = Modifier
) {
    val messages by viewModel.messages.collectAsState()
    val threadAddress by viewModel.threadAddress.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    
    var messageText by remember { mutableStateOf("") }
    val focusRequester = remember { FocusRequester() }
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    
    // Track if this is the first load
    var firstLoad by remember { mutableStateOf(true) }
    var previousMessageCount by remember { mutableStateOf(0) }
    
    LaunchedEffect(threadId) {
        viewModel.loadThread(threadId)
        firstLoad = true
        previousMessageCount = 0
    }
    
    // Smart auto-scroll: only scroll when new messages arrive AND user is near bottom
    LaunchedEffect(messages.size) {
        val currentMessageCount = messages.size
        if (currentMessageCount > 0) {
            val visibleItems = listState.layoutInfo.visibleItemsInfo
            val lastVisibleIndex = visibleItems.lastOrNull()?.index ?: -1
            val totalItems = currentMessageCount
            
            // Check if user is near bottom (within 2 items from the end)
            val isNearBottom = lastVisibleIndex >= totalItems - 2
            
            // Check if this is a new message (count increased)
            val hasNewMessage = currentMessageCount > previousMessageCount
            
            // Only auto-scroll if:
            // 1. It's the first load, OR
            // 2. New message arrived AND user is already near bottom
            if (firstLoad || (hasNewMessage && isNearBottom)) {
                scope.launch {
                    listState.animateScrollToItem(totalItems - 1)
                }
                firstLoad = false
            }
            
            previousMessageCount = currentMessageCount
        }
    }
    
    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopAppBar(
                title = { Text(threadAddress) },
                navigationIcon = {
                    TextButton(onClick = onBack) {
                        Text("Back")
                    }
                }
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            // Messages list
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
            ) {
                if (isLoading && messages.isEmpty()) {
                    CircularProgressIndicator(
                        modifier = Modifier.align(Alignment.Center)
                    )
                } else if (messages.isEmpty()) {
                    Text(
                        text = "No messages",
                        modifier = Modifier.align(Alignment.Center),
                        style = MaterialTheme.typography.bodyLarge
                    )
                } else {
                    LazyColumn(
                        state = listState,
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(
                            horizontal = 8.dp,
                            vertical = 16.dp
                        ),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(
                            items = messages,
                            key = { it.id }
                        ) { message ->
                            MessageBubble(
                                message = message,
                                modifier = Modifier.fillMaxWidth(),
                                onCopy = { /* Already handled in MessageBubble */ },
                                onDelete = {
                                    viewModel.deleteMessage(message.id)
                                },
                                onForward = {
                                    // TODO: Implement forward functionality
                                },
                                onReport = {
                                    onMessageClick(message.id)
                                }
                            )
                        }
                    }
                }
            }
            
            // Message input
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(8.dp),
                verticalAlignment = Alignment.Bottom
            ) {
                OutlinedTextField(
                    value = messageText,
                    onValueChange = { messageText = it },
                    modifier = Modifier
                        .weight(1f)
                        .focusRequester(focusRequester),
                    placeholder = { Text("Type a message...") },
                    maxLines = 4
                )
                
                Spacer(modifier = Modifier.width(8.dp))
                
                FloatingActionButton(
                    onClick = {
                        if (messageText.isNotBlank()) {
                            viewModel.sendMessage(context, threadAddress, messageText)
                            messageText = ""
                        }
                    },
                    modifier = Modifier.size(56.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Send,
                        contentDescription = "Send"
                    )
                }
            }
        }
    }
}

