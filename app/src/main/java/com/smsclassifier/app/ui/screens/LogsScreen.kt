package com.smsclassifier.app.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.data.MisclassificationLogEntity
import com.smsclassifier.app.ui.viewmodel.LogsViewModel
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LogsScreen(
    viewModel: LogsViewModel,
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val logs by viewModel.logs.collectAsState()
    val context = LocalContext.current
    val snackbarHostState = remember { SnackbarHostState() }
    val coroutineScope = rememberCoroutineScope()

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopAppBar(
                title = { Text("Misclassification logs") },
                navigationIcon = {
                    TextButton(onClick = onBack) { Text("Back") }
                },
                actions = {
                    TextButton(onClick = { shareLogs(context, viewModel, logs, snackbarHostState, coroutineScope) }) {
                        Text("Share all")
                    }
                    TextButton(onClick = {
                        viewModel.clear()
                    }) {
                        Text("Clear")
                    }
                }
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { innerPadding ->
        if (logs.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
                contentAlignment = Alignment.Center
            ) {
                Text("No logs yet.")
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                items(logs, key = { it.id }) { log ->
                    LogCard(
                        log = log,
                        onShare = {
                            shareSingleLog(context, viewModel, log, snackbarHostState, coroutineScope)
                        },
                        onDelete = { viewModel.delete(log) }
                    )
                }
            }
        }
    }
}

@Composable
private fun LogCard(
    log: MisclassificationLogEntity,
    onShare: () -> Unit,
    onDelete: () -> Unit
) {
    Card {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(text = log.sender, style = MaterialTheme.typography.titleMedium)
            Text(text = log.body, style = MaterialTheme.typography.bodyMedium)
            Text(
                text = "OTP: ${log.predictedIsOtp} • Intent: ${log.predictedOtpIntent ?: "N/A"} • Phishing: ${log.predictedIsPhishing}",
                style = MaterialTheme.typography.labelSmall
            )
            log.userNote?.takeIf { it.isNotBlank() }?.let {
                Text(text = "User note: $it", style = MaterialTheme.typography.bodySmall)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilledTonalIconButton(onClick = onShare) {
                    Icon(Icons.Default.Share, contentDescription = "Share log")
                }
                FilledTonalIconButton(onClick = onDelete) {
                    Icon(Icons.Default.Delete, contentDescription = "Delete log")
                }
            }
        }
    }
}

private fun shareLogs(
    context: android.content.Context,
    viewModel: LogsViewModel,
    logs: List<MisclassificationLogEntity>,
    snackbarHostState: SnackbarHostState,
    coroutineScope: CoroutineScope
) {
    viewModel.exportAll(context, logs) { uri ->
        coroutineScope.launch {
            if (uri == null) {
                snackbarHostState.showSnackbar("No logs to share.")
            } else {
                startShareIntent(context, uri)
            }
        }
    }
}

private fun shareSingleLog(
    context: android.content.Context,
    viewModel: LogsViewModel,
    log: MisclassificationLogEntity,
    snackbarHostState: SnackbarHostState,
    coroutineScope: CoroutineScope
) {
    viewModel.exportSingle(context, log) { uri ->
        coroutineScope.launch {
            if (uri == null) {
                snackbarHostState.showSnackbar("Unable to prepare log.")
            } else {
                startShareIntent(context, uri)
            }
        }
    }
}

private fun startShareIntent(context: android.content.Context, uri: Uri) {
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "text/csv"
        putExtra(Intent.EXTRA_STREAM, uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    context.startActivity(Intent.createChooser(intent, "Share logs"))
}


