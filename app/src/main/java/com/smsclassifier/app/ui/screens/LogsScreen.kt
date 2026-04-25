package com.smsclassifier.app.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.BugReport
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.data.MisclassificationLogEntity
import com.smsclassifier.app.ui.viewmodel.LogsViewModel
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

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
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        "Reports",
                        fontWeight = FontWeight.SemiBold,
                        style = MaterialTheme.typography.titleMedium
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    if (logs.isNotEmpty()) {
                        IconButton(onClick = {
                            shareLogs(context, viewModel, logs, snackbarHostState, coroutineScope)
                        }) {
                            Icon(Icons.Default.Share, contentDescription = "Share all")
                        }
                        IconButton(onClick = { viewModel.clear() }) {
                            Icon(Icons.Default.Delete, contentDescription = "Clear all")
                        }
                    }
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(MaterialTheme.colorScheme.background)
        ) {
            if (logs.isEmpty()) {
                EmptyLogsState(modifier = Modifier.align(Alignment.Center).padding(24.dp))
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
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
}

@Composable
private fun EmptyLogsState(modifier: Modifier = Modifier) {
    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Box(
            modifier = Modifier
                .size(96.dp)
                .clip(CircleShape)
                .background(MaterialTheme.colorScheme.primaryContainer),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = Icons.Default.BugReport,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(48.dp)
            )
        }
        Text(
            text = "No reports yet",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold
        )
        Text(
            text = "When you tap \"Report as wrong\" on a message, it shows up here. Use it to track classifier mistakes.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun LogCard(
    log: MisclassificationLogEntity,
    onShare: () -> Unit,
    onDelete: () -> Unit
) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 1.dp,
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = log.sender,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.weight(1f)
                )
                Text(
                    text = formatLogDate(log.createdAt),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Text(text = log.body, style = MaterialTheme.typography.bodyMedium)
            Surface(
                color = MaterialTheme.colorScheme.surfaceVariant,
                shape = RoundedCornerShape(10.dp)
            ) {
                Column(
                    modifier = Modifier.padding(10.dp),
                    verticalArrangement = Arrangement.spacedBy(2.dp)
                ) {
                    PredictionLine("Predicted OTP", log.predictedIsOtp?.toString() ?: "—")
                    PredictionLine("Predicted intent", log.predictedOtpIntent ?: "—")
                    PredictionLine("Predicted phishing", log.predictedIsPhishing?.toString() ?: "—")
                }
            }
            log.userNote?.takeIf { it.isNotBlank() }?.let {
                Text(
                    text = "Your note: $it",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilledTonalButton(onClick = onShare) {
                    Icon(
                        Icons.Default.Share,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Share")
                }
                TextButton(onClick = onDelete) {
                    Icon(
                        Icons.Default.Delete,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Delete")
                }
            }
        }
    }
}

@Composable
private fun PredictionLine(label: String, value: String) {
    Row {
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.weight(1f)
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodySmall,
            fontWeight = FontWeight.Medium
        )
    }
}

private fun formatLogDate(ts: Long): String =
    SimpleDateFormat("MMM d, h:mm a", Locale.getDefault()).format(Date(ts))

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
    // Create email intent with recipient pre-filled
    val emailIntent = Intent(Intent.ACTION_SEND).apply {
        type = "text/csv"
        putExtra(Intent.EXTRA_EMAIL, arrayOf("gandharv@musicaigeneration.com"))
        putExtra(Intent.EXTRA_SUBJECT, "SMS Misclassification Logs")
        putExtra(Intent.EXTRA_STREAM, uri)
        putExtra(Intent.EXTRA_TEXT, "Please find attached the misclassification logs.")
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    
    // Filter to show only email apps first
    val emailChooser = Intent.createChooser(emailIntent, "Share logs via email")
    
    // Create a generic share intent as fallback
    val genericIntent = Intent(Intent.ACTION_SEND).apply {
        type = "text/csv"
        putExtra(Intent.EXTRA_STREAM, uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    
    // Add fallback to chooser
    emailChooser.putExtra(Intent.EXTRA_INITIAL_INTENTS, arrayOf(genericIntent))
    context.startActivity(emailChooser)
}


