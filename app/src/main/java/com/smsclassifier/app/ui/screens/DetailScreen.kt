package com.smsclassifier.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.ui.badges.ClassificationBadge
import com.smsclassifier.app.ui.badges.SensitivityBadge
import com.smsclassifier.app.ui.components.ReasonChips
import com.smsclassifier.app.ui.viewmodel.DetailViewModel
import com.smsclassifier.app.util.ClassificationUtils
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonPrimitive

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DetailScreen(
    messageId: Long,
    viewModel: DetailViewModel,
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val message by viewModel.message.collectAsState()
    
    LaunchedEffect(messageId) {
        viewModel.loadMessage(messageId)
    }

    val snackbarHostState = remember { SnackbarHostState() }
    val clipboardManager = LocalClipboardManager.current
    val coroutineScope = rememberCoroutineScope()

    var showReportDialog by remember { mutableStateOf(false) }
    var reportNote by remember { mutableStateOf("") }
    var reportType by remember { mutableStateOf<String?>(null) }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = { Text("Message Details") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Text("Back")
                    }
                }
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { /* Share */ }) {
                Icon(Icons.Default.Share, contentDescription = "Share")
            }
        }
    ) { padding ->
        message?.let { msg ->
            Column(
                modifier = modifier
                    .fillMaxSize()
                    .padding(padding)
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Sender and timestamp
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = msg.sender,
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = formatTimestamp(msg.ts),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                
                Divider()
                
                // Message body
                Text(
                    text = msg.body,
                    style = MaterialTheme.typography.bodyLarge
                )
                
                Divider()
                
                // Classification badges
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    ClassificationBadge(type = ClassificationUtils.riskBadgeType(msg))
                    SensitivityBadge(type = ClassificationUtils.sensitivityType(msg))
                }
                
                // OTP Intent
                if (msg.otpIntent != null) {
                    Text(
                        text = "OTP Intent: ${msg.otpIntent}",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Medium
                    )
                }

                val otpCode = remember(msg.body) { ClassificationUtils.extractOtpCode(msg.body) }
                if (otpCode != null) {
                    FilledTonalButton(
                        onClick = {
                            clipboardManager.setText(AnnotatedString(otpCode))
                            coroutineScope.launch {
                                snackbarHostState.showSnackbar("OTP copied to clipboard")
                            }
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Copy OTP ($otpCode)")
                    }
                }
                
                // Phishing score
                if (msg.phishScore != null) {
                    Text(
                        text = "Phishing Score: ${String.format("%.2f", msg.phishScore)}",
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
                
                // Reasons
                val reasons = parseReasons(msg.reasonsJson)
                if (reasons.isNotEmpty()) {
                    Column {
                        Text(
                            text = "Reasons:",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        ReasonChips(reasons = reasons)
                    }
                }
                
                // Report as wrong button
                Button(
                    onClick = {
                        reportNote = ""
                        showReportDialog = true
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Report as Wrong")
                }
            }
        } ?: run {
            Box(modifier = Modifier.fillMaxSize()) {
                CircularProgressIndicator()
            }
        }
    }

    if (showReportDialog) {
        AlertDialog(
            onDismissRequest = { 
                showReportDialog = false
                reportNote = ""
                reportType = null
            },
            title = { Text("Report Classification Issue") },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    Text(
                        text = "What's wrong with the classification?",
                        style = MaterialTheme.typography.titleSmall
                    )
                    
                    // Report type options
                    val reportTypes = listOf(
                        "Should be OTP" to "This message should be classified as OTP",
                        "Should not be OTP" to "This message should NOT be classified as OTP",
                        "Wrong OTP intent" to "The OTP intent category is incorrect",
                        "Should be phishing" to "This message should be flagged as phishing",
                        "Should not be phishing" to "This message should NOT be flagged as phishing"
                    )
                    
                    reportTypes.forEach { (type, description) ->
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            RadioButton(
                                selected = reportType == type,
                                onClick = { 
                                    reportType = type
                                    // Pre-fill note based on type
                                    reportNote = description
                                }
                            )
                            Text(
                                text = type,
                                modifier = Modifier.weight(1f),
                                style = MaterialTheme.typography.bodyMedium
                            )
                        }
                    }
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    OutlinedTextField(
                        value = reportNote,
                        onValueChange = { reportNote = it },
                        label = { Text("Additional details (optional)") },
                        placeholder = { Text("Provide more context if needed...") },
                        modifier = Modifier.fillMaxWidth(),
                        minLines = 2,
                        maxLines = 4
                    )
                }
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        val finalNote = if (reportType != null) {
                            "$reportType. $reportNote".trim()
                        } else {
                            reportNote
                        }
                        viewModel.reportAsWrong(finalNote)
                        showReportDialog = false
                        reportNote = ""
                        reportType = null
                    },
                    enabled = reportType != null || reportNote.isNotBlank()
                ) {
                    Text("Submit")
                }
            },
            dismissButton = {
                TextButton(onClick = { 
                    showReportDialog = false
                    reportNote = ""
                    reportType = null
                }) {
                    Text("Cancel")
                }
            }
        )
    }
}

private fun parseReasons(json: String?): List<String> {
    if (json.isNullOrBlank()) return emptyList()
    return try {
        Json.parseToJsonElement(json).jsonArray.map { it.jsonPrimitive.content }
    } catch (e: Exception) {
        emptyList()
    }
}

private fun formatTimestamp(ts: Long): String {
    val now = System.currentTimeMillis()
    val diff = now - ts
    return when {
        diff < 60000 -> "${diff / 1000}s ago"
        diff < 3600000 -> "${diff / 60000}m ago"
        diff < 86400000 -> "${diff / 3600000}h ago"
        else -> "${diff / 86400000}d ago"
    }
}

