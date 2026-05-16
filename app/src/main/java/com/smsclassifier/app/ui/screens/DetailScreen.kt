package com.smsclassifier.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.text.style.TextOverflow
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.data.SettingsRepository
import com.smsclassifier.app.ui.badges.ClassificationBadge
import com.smsclassifier.app.ui.badges.SensitivityBadge
import com.smsclassifier.app.ui.components.ReasonChips
import com.smsclassifier.app.ui.viewmodel.DetailViewModel
import com.smsclassifier.app.util.ClassificationUtils
import com.smsclassifier.app.util.SmsRedactor
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
    onOpenPaywall: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    val message by viewModel.message.collectAsState()
    val isRetrying by viewModel.isRetrying.collectAsState()
    
    LaunchedEffect(messageId) {
        viewModel.loadMessage(messageId)
    }
    
    // Reload message when retry completes
    LaunchedEffect(isRetrying) {
        if (!isRetrying) {
            viewModel.loadMessage(messageId)
        }
    }

    val snackbarHostState = remember { SnackbarHostState() }
    val clipboardManager = LocalClipboardManager.current
    val coroutineScope = rememberCoroutineScope()
    val entitlementManager = AppContainer.entitlementManager
    val trialAvailable = !entitlementManager.hasTrialStarted()

    var showReportDialog by remember { mutableStateOf(false) }
    var reportNote by remember { mutableStateOf("") }
    var reportType by remember { mutableStateOf<String?>(null) }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        "Message details",
                        fontWeight = FontWeight.SemiBold,
                        style = MaterialTheme.typography.titleMedium
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
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

                if (AppContainer.entitlementManager.shouldShowDetailUnlockPlaceholder(msg)) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.secondaryContainer
                        )
                    ) {
                        Column(
                            modifier = Modifier.padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Text(
                                text = "Cloud classification locked",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.SemiBold
                            )
                            Text(
                                text = if (trialAvailable) {
                                    "Cloud phishing risk is unavailable here. Start the 7-day Pro trial or unlock Pro for phishing scores, cloud OTP intent, and full server classification."
                                } else {
                                    "Cloud phishing risk is unavailable here. Unlock Pro for phishing scores, cloud OTP intent, and full server classification."
                                },
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSecondaryContainer
                            )
                            Button(
                                onClick = {
                                    AppContainer.telemetry.logEvent(
                                        "pro_feature_blocked",
                                        mapOf("surface" to "detail")
                                    )
                                    onOpenPaywall()
                                },
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text(if (trialAvailable) "Start trial / Unlock Pro" else "Unlock Pro")
                            }
                        }
                    }
                    Divider()
                }

                // Message body
                Text(
                    text = msg.body,
                    style = MaterialTheme.typography.bodyLarge
                )
                
                Divider()
                
                val hasCloudRiskResult = msg.isPhishing != null || msg.phishScore != null
                val sensitivity = ClassificationUtils.sensitivityType(msg)
                if (hasCloudRiskResult || sensitivity != com.smsclassifier.app.ui.badges.SensitivityType.NONE) {
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        if (hasCloudRiskResult) {
                            ClassificationBadge(type = ClassificationUtils.riskBadgeType(msg))
                        }
                        SensitivityBadge(type = sensitivity)
                    }
                }
                
                // OTP Intent
                if (msg.otpIntent != null) {
                    Text(
                        text = "OTP Intent: ${msg.otpIntent}",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Medium
                    )
                }

                val otpCode = remember(msg.body, msg.sender, msg.isOtp) {
                    ClassificationUtils.extractOtpForCopy(msg.body, msg.sender, msg.isOtp)
                }
                if (otpCode != null) {
                    FilledTonalButton(
                        onClick = {
                            clipboardManager.setText(AnnotatedString(otpCode))
                            AppContainer.telemetry.logOtpCopied("detail")
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
                
                // Check if classification failed (all null and error in reasons)
                val reasons = parseReasons(msg.reasonsJson)
                val hasError = msg.isOtp == null && msg.isPhishing == null && 
                    reasons.any { it.contains("error", ignoreCase = true) || 
                                 it.contains("unable", ignoreCase = true) ||
                                 it.contains("failed", ignoreCase = true) ||
                                 it.contains("timeout", ignoreCase = true) }
                
                if (hasError) {
                    // Show error state
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.errorContainer
                        )
                    ) {
                        Column(
                            modifier = Modifier.padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Text(
                                text = "Classification Error",
                                style = MaterialTheme.typography.titleMedium,
                                color = MaterialTheme.colorScheme.onErrorContainer,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = reasons.firstOrNull { 
                                    it.contains("error", ignoreCase = true) || 
                                    it.contains("unable", ignoreCase = true) ||
                                    it.contains("failed", ignoreCase = true) ||
                                    it.contains("timeout", ignoreCase = true)
                                } ?: "Unable to classify this message",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onErrorContainer
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            Button(
                                onClick = {
                                    AppContainer.telemetry.logCtaTap("detail", "retry_classification")
                                    viewModel.retryClassification()
                                },
                                enabled = !isRetrying,
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Row(
                                    horizontalArrangement = Arrangement.Center,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    if (isRetrying) {
                                        CircularProgressIndicator(
                                            modifier = Modifier.size(16.dp),
                                            color = MaterialTheme.colorScheme.onPrimary,
                                            strokeWidth = 2.dp
                                        )
                                        Spacer(modifier = Modifier.width(8.dp))
                                    }
                                    Text(if (isRetrying) "Retrying..." else "Retry Classification")
                                }
                            }
                        }
                    }
                } else if (reasons.isNotEmpty()) {
                    // Show classification reasons
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
                        AppContainer.telemetry.logEvent(
                            "feedback_started",
                            mapOf("surface" to "detail")
                        )
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
                val previewMsg = message
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    if (previewMsg != null) {
                        val ctx = LocalContext.current
                        val installId = SettingsRepository(ctx).installId
                        val redactedBody = SmsRedactor.redactForTraining(previewMsg.body, installId)
                        Text(
                            text = "Upload preview (digits redacted like server upload):",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = redactedBody,
                            style = MaterialTheme.typography.bodySmall,
                            maxLines = 4,
                            overflow = TextOverflow.Ellipsis,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
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
                        val correctionKind = when (reportType) {
                            "Should be OTP" -> "actually_otp"
                            "Should not be OTP" -> "not_otp"
                            "Wrong OTP intent" -> "other"
                            "Should be phishing" -> "phishing"
                            "Should not be phishing" -> "not_phishing"
                            else -> "other"
                        }
                        viewModel.reportAsWrong(correctionKind, finalNote)
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
                    AppContainer.telemetry.logEvent(
                        "feedback_cancelled",
                        mapOf("surface" to "detail")
                    )
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

