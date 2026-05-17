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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CloudUpload
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.PrivacyTip
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
import com.smsclassifier.app.ui.components.AppScaffold
import com.smsclassifier.app.ui.theme.Spacing
import com.smsclassifier.app.ui.viewmodel.SettingsViewModel
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    viewModel: SettingsViewModel,
    onBack: () -> Unit,
    onNavigateToNotifications: () -> Unit,
    onNavigateToExport: () -> Unit,
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

    LaunchedEffect(Unit) {
        viewModel.refreshDefaultSmsStatus()
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
    AppScaffold(
        title = "Settings",
        onBack = onBack,
        snackbarHostState = snackbarHostState,
        modifier = Modifier.fillMaxSize(),
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = Spacing.xl, vertical = Spacing.lg),
            verticalArrangement = Arrangement.spacedBy(Spacing.xl)
        ) {
            SettingsSection(title = "General") {
                SettingsRow(
                    icon = Icons.Default.Phone,
                    title = "Default SMS app",
                    subtitle = if (isDefaultSms)
                        "Handles SMS for this phone"
                    else
                        "Make this app your default to get SMS",
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
                    subtitle = "Manage alerts in Android settings",
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

            SettingsSection(title = "Privacy & data") {
                ToggleRow(
                    title = "Help us improve the app",
                    subtitle = "Share feature usage only. Message content is never included.",
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
                SettingsRow(
                    icon = Icons.Default.CloudUpload,
                    title = "Improve wrong-label fixes",
                    subtitle = "Optional wrong-label details; off by default.",
                    trailing = {
                        Switch(
                            checked = feedbackUploadEnabled,
                            onCheckedChange = { on ->
                                if (!on) {
                                    viewModel.setFeedbackUploadEnabled(false)
                                } else if (!viewModel.feedbackConsentAlreadyAcknowledged()) {
                                    showFeedbackConsentDialog = true
                                } else {
                                    viewModel.setFeedbackUploadEnabled(true)
                                }
                            }
                        )
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
                    subtitle = "One zip with labels, full export, and wrong-label reports",
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
                    subtitle = "Remove data linked to this install",
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

            SettingsSection(title = "Pro") {
                SettingsRow(
                    icon = Icons.Default.Star,
                    title = "Upgrade to Pro",
                    subtitle = "One-time purchase for scam warnings and risk scores",
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
            }

            SettingsSection(title = "Help") {
                SettingsRow(
                    icon = Icons.Default.Email,
                    title = "Contact developer",
                    subtitle = "Feedback, bug reports, and ideas",
                    trailing = {
                        FilledTonalButton(onClick = { viewModel.contactDeveloper() }) {
                            Text("Email")
                        }
                    }
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
                    title = { Text("Improve wrong-label fixes?") },
                    text = {
                        Text(
                            "Send the text and sender of misclassified messages over HTTPS so we can improve the classifier. " +
                                "Stored on our servers — see Privacy policy. Off by default."
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
                                                "Can't reach us right now. Try again."
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
