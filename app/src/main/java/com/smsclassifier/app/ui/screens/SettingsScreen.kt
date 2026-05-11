package com.smsclassifier.app.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.CloudDone
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CloudUpload
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.PrivacyTip
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.BuildConfig
import com.smsclassifier.app.R
import com.smsclassifier.app.ui.viewmodel.SettingsViewModel
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    viewModel: SettingsViewModel,
    onBack: () -> Unit,
    onOpenMisclassificationLogs: () -> Unit,
    onNavigateToNotifications: () -> Unit,
    onNavigateToExport: () -> Unit,
    onNavigateToDiagnostics: () -> Unit,
    onNavigateToAbout: () -> Unit,
    onNavigateToPaywall: () -> Unit = {},
    onNavigateToConsent: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    val isDefaultSms by viewModel.isDefaultSmsApp.collectAsState()
    val context = LocalContext.current
    val activity = remember(context) { context.findActivity() }
    val snackbarHostState = remember { SnackbarHostState() }
    val coroutineScope = rememberCoroutineScope()
    val feedbackUploadEnabled by viewModel.feedbackUploadEnabled.collectAsState()
    var showFeedbackConsentDialog by remember { mutableStateOf(false) }
    var deleteConfirm by remember { mutableStateOf(false) }
    var deleteLoading by remember { mutableStateOf(false) }

    val analyticsConsent by AppContainer.consentManager.analyticsConsent.collectAsState(
        initial = AppContainer.consentManager.analyticsEnabledNow()
    )
    val crashConsent by AppContainer.consentManager.crashlyticsConsent.collectAsState(
        initial = AppContainer.consentManager.crashlyticsEnabledNow()
    )
    val metaConsent by AppContainer.consentManager.metaAdsConsent.collectAsState(
        initial = AppContainer.consentManager.metaAdsEnabledNow()
    )

    LaunchedEffect(Unit) {
        viewModel.refreshDefaultSmsStatus()
        viewModel.checkBackendHealth()
    }

    val exportError by viewModel.lastExportError.collectAsState()
    LaunchedEffect(exportError) {
        exportError?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.consumeExportError()
        }
    }

    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) {
        viewModel.refreshDefaultSmsStatus()
    }

    Box(modifier = modifier.fillMaxSize()) {
    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text("Settings", fontWeight = FontWeight.SemiBold)
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
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            SettingsSection(title = "General") {
                SettingsRow(
                    icon = Icons.Default.Phone,
                    title = "Default SMS app",
                    subtitle = if (isDefaultSms)
                        "This app handles all SMS on your phone"
                    else
                        "Set this app as your default to receive SMS",
                    trailing = {
                        if (!isDefaultSms) {
                            FilledTonalButton(
                                onClick = {
                                    val intent = viewModel.createDefaultSmsIntent()
                                    if (intent != null && activity != null) launcher.launch(intent)
                                }
                            ) { Text("Set default") }
                        } else {
                            Text(
                                text = "Active",
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.primary,
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                    }
                )
                SectionDivider()
                SettingsRow(
                    icon = Icons.Default.Notifications,
                    title = "Notifications",
                    subtitle = "Sound, vibration, system settings",
                    trailing = {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowForward,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    },
                    onClick = onNavigateToNotifications
                )
            }

            ClassifierSection(
                viewModel = viewModel,
                feedbackUploadEnabled = feedbackUploadEnabled,
                onFeedbackToggleOff = { viewModel.setFeedbackUploadEnabled(false) },
                onFeedbackToggleOnConsentNeeded = { showFeedbackConsentDialog = true },
                onFeedbackToggleOnGranted = { viewModel.setFeedbackUploadEnabled(true) },
                onOpenMisclassificationLogs = onOpenMisclassificationLogs
            )

            SettingsSection(title = "Privacy & data") {
                ToggleRow(
                    title = "Anonymous usage analytics",
                    subtitle = "Helps us understand which features are used (no SMS content).",
                    checked = analyticsConsent,
                    onCheckedChange = { on ->
                    coroutineScope.launch {
                        AppContainer.consentManager.setAnalyticsConsent(on)
                        AppContainer.telemetry.logConsentChanged("analytics", on)
                    }
                    }
                )
                SectionDivider()
                ToggleRow(
                    title = "Crash reports",
                    subtitle = "Helps us fix bugs. No message text is included.",
                    checked = crashConsent,
                    onCheckedChange = { on ->
                    coroutineScope.launch {
                        AppContainer.consentManager.setCrashlyticsConsent(on)
                        AppContainer.telemetry.logConsentChanged("crash_reports", on)
                    }
                    }
                )
                SectionDivider()
                ToggleRow(
                    title = "Ad campaign measurement (Meta)",
                    subtitle = "Only if you run or see our ads; uses limited device signals.",
                    checked = metaConsent,
                    onCheckedChange = { on ->
                    coroutineScope.launch {
                        AppContainer.consentManager.setMetaAdsConsent(on)
                        AppContainer.telemetry.logConsentChanged("meta_ads", on)
                    }
                    }
                )
                SectionDivider()
                SettingsRow(
                    icon = Icons.Default.PrivacyTip,
                    title = "Privacy policy",
                    subtitle = "Opens in browser",
                    trailing = {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowForward,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    },
                    onClick = {
                        context.startActivity(
                            Intent(Intent.ACTION_VIEW, Uri.parse(context.getString(R.string.privacy_policy_url)))
                        )
                    }
                )
                SectionDivider()
                SettingsRow(
                    icon = Icons.Default.Description,
                    title = "Export my data",
                    subtitle = "Labels, full classification dump, misclassification reports",
                    trailing = {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowForward,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    },
                    onClick = onNavigateToExport
                )
                SectionDivider()
                SettingsRow(
                    icon = Icons.Default.DeleteOutline,
                    title = "Delete my data",
                    subtitle = "Request deletion of data tied to this install",
                    trailing = {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowForward,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    },
                    onClick = {
                        if (!deleteLoading) deleteConfirm = true
                    }
                )
            }

            SettingsSection(title = "Help") {
                SettingsRow(
                    icon = Icons.Default.Star,
                    title = "Upgrade to Pro",
                    subtitle = "One-time purchase — full cloud classification",
                    trailing = {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowForward,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    },
                    onClick = {
                        onNavigateToPaywall()
                    }
                )
                SectionDivider()
                SettingsRow(
                    icon = Icons.Default.Email,
                    title = "Contact developer",
                    subtitle = "Send feedback, bug reports, or feature ideas",
                    trailing = {
                        FilledTonalButton(onClick = { viewModel.contactDeveloper() }) {
                            Text("Email")
                        }
                    }
                )
                SectionDivider()
                SettingsRow(
                    icon = Icons.Default.Settings,
                    title = "Diagnostics & self-test",
                    subtitle = "Performance, OTP plumbing, technical details",
                    trailing = {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowForward,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    },
                    onClick = onNavigateToDiagnostics
                )
                SectionDivider()
                SettingsRow(
                    icon = Icons.Filled.Info,
                    title = "About",
                    subtitle = "Version and notices",
                    trailing = {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowForward,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    },
                    onClick = onNavigateToAbout
                )
            }

            if (showFeedbackConsentDialog) {
                AlertDialog(
                    onDismissRequest = { showFeedbackConsentDialog = false },
                    title = { Text("Share misclassification reports?") },
                    text = {
                        Text(
                            "When this is on, each time you tap \"Report as wrong\" we send the SMS text, sender, predicted labels, your note, app version, and an anonymous install id over HTTPS so we can improve the classifier.\n\n" +
                                "This is stored on our servers indefinitely for ML training unless you email us to request deletion. See our privacy policy."
                        )
                    },
                    confirmButton = {
                        TextButton(
                            onClick = {
                                viewModel.markFeedbackConsentAcknowledged()
                                viewModel.setFeedbackUploadEnabled(true)
                                showFeedbackConsentDialog = false
                            }
                        ) { Text("Turn on") }
                    },
                    dismissButton = {
                        TextButton(onClick = { showFeedbackConsentDialog = false }) {
                            Text("Cancel")
                        }
                    }
                )
            }

            if (deleteConfirm) {
                AlertDialog(
                    onDismissRequest = { if (!deleteLoading) deleteConfirm = false },
                    title = { Text("Delete my data") },
                    text = {
                        Text(
                            buildAnnotatedString {
                                append(
                                    "This permanently removes all SMS classifications, feedback, " +
                                        "and account data on this device. "
                                )
                                withStyle(SpanStyle(fontWeight = FontWeight.Bold)) {
                                    append("Your purchase will be preserved by Google Play.")
                                }
                                append(" Continue?")
                            }
                        )
                    },
                    confirmButton = {
                        TextButton(
                            enabled = !deleteLoading,
                            onClick = {
                                coroutineScope.launch {
                                    deleteLoading = true
                                    deleteConfirm = false
                                    val result = viewModel.deleteAllData()
                                    deleteLoading = false
                                    result.fold(
                                        onSuccess = {
                                            snackbarHostState.showSnackbar("All data deleted.")
                                            if (!AppContainer.consentManager.onboardingSeenNow()) {
                                                onNavigateToConsent()
                                            }
                                        },
                                        onFailure = {
                                            snackbarHostState.showSnackbar(
                                                "Couldn't reach server, try again."
                                            )
                                        }
                                    )
                                }
                            }
                        ) { Text("Delete") }
                    },
                    dismissButton = {
                        TextButton(
                            onClick = { deleteConfirm = false },
                            enabled = !deleteLoading
                        ) { Text("Cancel") }
                    }
                )
            }

            if (BuildConfig.DEBUG) {
                TextButton(
                    onClick = {
                        val id =
                            com.smsclassifier.app.data.SettingsRepository(context).installId
                        viewModel.openDeleteDataEmailFallback(id)
                    },
                    modifier = Modifier.padding(horizontal = 8.dp)
                ) {
                    Text("Debug: email delete-data request")
                }
            }

            Spacer(modifier = Modifier.height(8.dp))
        }
    }
        if (deleteLoading) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(24.dp),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator()
            }
        }
    }
}

@Composable
private fun ClassifierSection(
    viewModel: SettingsViewModel,
    feedbackUploadEnabled: Boolean,
    onFeedbackToggleOff: () -> Unit,
    onFeedbackToggleOnConsentNeeded: () -> Unit,
    onFeedbackToggleOnGranted: () -> Unit,
    onOpenMisclassificationLogs: () -> Unit
) {
    val backendHealth by viewModel.backendHealthStatus.collectAsState()
    val isCheckingHealth by viewModel.isCheckingBackendHealth.collectAsState()

    SettingsSection(title = "Classifier") {
        SettingsRow(
            icon = Icons.Default.Memory,
            title = "Inference mode",
            subtitle = "Server ensemble (fixed)",
            trailing = null
        )
        SectionDivider()
        SettingsRow(
            icon = if (backendHealth?.isHealthy == true) Icons.Default.CloudDone else Icons.Default.CloudOff,
            title = "Backend status",
            subtitle = when (val s = backendHealth) {
                null -> "Unknown"
                else -> {
                    val ms = s.responseTimeMs?.let { " · ${it}ms" } ?: ""
                    if (s.isHealthy) "Healthy$ms"
                    else (s.errorMessage ?: "Unhealthy") + ms
                }
            },
            trailing = {
                if (isCheckingHealth) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        strokeWidth = 2.dp
                    )
                } else {
                    IconButton(onClick = { viewModel.checkBackendHealth() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh backend status")
                    }
                }
            }
        )
        SectionDivider()
        SettingsRow(
            icon = Icons.Default.Description,
            title = "Misclassification logs",
            subtitle = "Review messages you marked as wrong",
            trailing = {
                TextButton(onClick = onOpenMisclassificationLogs) {
                    Text("Open")
                }
            }
        )
        SectionDivider()
        SettingsRow(
            icon = Icons.Default.CloudUpload,
            title = "Help improve classification",
            subtitle =
                "Send misclassification reports to the developer to improve the classifier. " +
                    "Off by default. Includes the SMS text and sender.",
            trailing = {
                Switch(
                    checked = feedbackUploadEnabled,
                    onCheckedChange = { on ->
                        if (!on) {
                            onFeedbackToggleOff()
                        } else if (!viewModel.feedbackConsentAlreadyAcknowledged()) {
                            onFeedbackToggleOnConsentNeeded()
                        } else {
                            onFeedbackToggleOnGranted()
                        }
                    }
                )
            }
        )
    }
}
