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
import com.smsclassifier.app.util.SenderNameResolver
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
    val context = LocalContext.current
    val entitlementManager = AppContainer.entitlementManager
    val trialAvailable = !entitlementManager.hasTrialStarted()
    val trialLabel = entitlementManager.trialDurationLabel()

    var showReportDialog by remember { mutableStateOf(false) }
    var reportNote by remember { mutableStateOf("") }
    var reportType by remember { mutableStateOf<ReportIssueOption?>(null) }
    var reportSubmitting by remember { mutableStateOf(false) }
    val reportSheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

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
            val friendlySender = SenderNameResolver.resolve(msg.sender)
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
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = friendlySender,
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold
                        )
                        if (friendlySender != msg.sender) {
                            Text(
                                text = msg.sender,
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
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
                                    "Scam warnings are unavailable here. Start a Pro trial ($trialLabel) or subscribe to Pro for scam warnings, code purpose, and full server classification."
                                } else {
                                    "Scam warnings are unavailable here. Subscribe to Pro for scam warnings, code purpose, and full server classification."
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
                                Text(if (trialAvailable) "Start trial / Subscribe" else "Subscribe")
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
                        text = "What this code is for: ${msg.otpIntent}",
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
                        text = "Scam warning score: ${String.format("%.2f", msg.phishScore)}",
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
                        reportType = null
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
        val closeSheet = {
            showReportDialog = false
            reportNote = ""
            reportType = null
            reportSubmitting = false
        }
        ModalBottomSheet(
            onDismissRequest = {
                AppContainer.telemetry.logEvent(
                    "feedback_cancelled",
                    mapOf("surface" to "detail")
                )
                closeSheet()
            },
            sheetState = reportSheetState
        ) {
            ReportClassificationSheet(
                redactedPreview = message?.let { previewMsg ->
                    val installId = SettingsRepository(context).installId
                    SmsRedactor.redactForTraining(previewMsg.body, installId)
                },
                selectedOption = reportType,
                note = reportNote,
                submitting = reportSubmitting,
                onOptionSelected = { reportType = it },
                onNoteChange = { reportNote = it },
                onCancel = {
                    AppContainer.telemetry.logEvent(
                        "feedback_cancelled",
                        mapOf("surface" to "detail")
                    )
                    closeSheet()
                },
                onSubmit = {
                    if (!reportSubmitting) {
                        val selected = reportType
                        val finalNote = buildString {
                            selected?.let { append(it.title).append(". ").append(it.description) }
                            if (reportNote.isNotBlank()) {
                                if (isNotBlank()) append(" ")
                                append(reportNote.trim())
                            }
                        }.trim()
                        reportSubmitting = true
                        val uploadsEnabled = SettingsRepository(context).feedbackUploadEnabled
                    viewModel.reportAsWrong(selected?.correctionKind ?: "other", finalNote) { saved ->
                        closeSheet()
                        coroutineScope.launch {
                            snackbarHostState.showSnackbar(
                                if (!saved) {
                                    "Report could not be saved. Try again."
                                } else if (uploadsEnabled) {
                                    "Report saved and queued for redacted upload."
                                } else {
                                    "Report saved on this phone. Turn on redacted uploads to send it."
                                    }
                                )
                            }
                        }
                    }
                }
            )
        }
    }
}

private data class ReportIssueOption(
    val title: String,
    val description: String,
    val correctionKind: String
)

private val reportIssueOptions = listOf(
    ReportIssueOption(
        title = "Should be OTP",
        description = "This message should be classified as OTP.",
        correctionKind = "actually_otp"
    ),
    ReportIssueOption(
        title = "Should not be OTP",
        description = "This message should not be classified as OTP.",
        correctionKind = "not_otp"
    ),
    ReportIssueOption(
        title = "Wrong code purpose",
        description = "The code type or purpose is incorrect.",
        correctionKind = "other"
    ),
    ReportIssueOption(
        title = "Should be scam",
        description = "This message should be marked as a scam.",
        correctionKind = "phishing"
    ),
    ReportIssueOption(
        title = "Should not be scam",
        description = "This message should not be marked as a scam.",
        correctionKind = "not_phishing"
    )
)

@Composable
private fun ReportClassificationSheet(
    redactedPreview: String?,
    selectedOption: ReportIssueOption?,
    note: String,
    submitting: Boolean,
    onOptionSelected: (ReportIssueOption) -> Unit,
    onNoteChange: (String) -> Unit,
    onCancel: () -> Unit,
    onSubmit: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .navigationBarsPadding()
            .imePadding()
            .padding(horizontal = 20.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(max = 560.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    text = "Report classification",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = "Tell us what looked wrong. This helps improve OTPs and scam warnings.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            if (!redactedPreview.isNullOrBlank()) {
                Surface(
                    shape = MaterialTheme.shapes.medium,
                    color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.55f),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(
                            text = "Upload preview",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = redactedPreview,
                            style = MaterialTheme.typography.bodyMedium,
                            maxLines = 4,
                            overflow = TextOverflow.Ellipsis,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    text = "What should be corrected?",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold
                )
                reportIssueOptions.forEach { option ->
                    FilterChip(
                        selected = selectedOption == option,
                        onClick = { if (!submitting) onOptionSelected(option) },
                        label = {
                            Column(modifier = Modifier.padding(vertical = 4.dp)) {
                                Text(option.title, style = MaterialTheme.typography.bodyMedium)
                                Text(
                                    option.description,
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        },
                        modifier = Modifier.fillMaxWidth(),
                        enabled = !submitting
                    )
                }
            }

            OutlinedTextField(
                value = note,
                onValueChange = onNoteChange,
                label = { Text("Any feedback for the developer? (optional)") },
                placeholder = { Text("Add context, expected label, or why this felt wrong.") },
                modifier = Modifier.fillMaxWidth(),
                minLines = 3,
                maxLines = 5,
                enabled = !submitting
            )
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp, Alignment.End),
            verticalAlignment = Alignment.CenterVertically
        ) {
            TextButton(onClick = onCancel, enabled = !submitting) {
                Text("Cancel")
            }
            Button(
                onClick = onSubmit,
                enabled = !submitting && (selectedOption != null || note.isNotBlank())
            ) {
                if (submitting) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(18.dp),
                        strokeWidth = 2.dp
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Submitting")
                } else {
                    Text("Submit report")
                }
            }
        }
        Spacer(modifier = Modifier.height(8.dp))
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

