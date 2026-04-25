package com.smsclassifier.app.ui.screens

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.BugReport
import androidx.compose.material.icons.filled.CloudDone
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.FileDownload
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.app.NotificationManagerCompat
import com.smsclassifier.app.ui.viewmodel.SettingsViewModel
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    viewModel: SettingsViewModel,
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val isDefaultSms by viewModel.isDefaultSmsApp.collectAsState()
    val context = LocalContext.current
    val activity = remember(context) { context.findActivity() }
    val snackbarHostState = remember { SnackbarHostState() }
    val coroutineScope = rememberCoroutineScope()

    var notificationSoundEnabled by remember { mutableStateOf(viewModel.notificationSoundEnabled) }
    var notificationVibrationEnabled by remember { mutableStateOf(viewModel.notificationVibrationEnabled) }
    val areNotificationsEnabled = remember {
        NotificationManagerCompat.from(context).areNotificationsEnabled()
    }

    LaunchedEffect(Unit) { viewModel.refreshDefaultSmsStatus() }

    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) {
        viewModel.refreshDefaultSmsStatus()
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
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
                .background(MaterialTheme.colorScheme.background)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {

            // === Section: SMS handler ===
            SettingsSection(title = "SMS handler") {
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
            }

            // === Section: Backend ===
            BackendSection(viewModel)

            // === Section: Performance ===
            PerformanceSection(viewModel)

            // === Section: Notifications ===
            NotificationsSection(
                areNotificationsEnabled = areNotificationsEnabled,
                soundEnabled = notificationSoundEnabled,
                vibrationEnabled = notificationVibrationEnabled,
                onSoundChange = {
                    notificationSoundEnabled = it
                    viewModel.setNotificationSoundEnabled(it)
                },
                onVibrationChange = {
                    notificationVibrationEnabled = it
                    viewModel.setNotificationVibrationEnabled(it)
                },
                onOpenAppNotifs = { viewModel.openNotificationSettings() },
                onOpenChannelNotifs = { viewModel.openNotificationChannelSettings() }
            )

            // === Section: Data export ===
            ExportSection(
                onExportLabels = {
                    viewModel.exportLabels { uri ->
                        coroutineScope.launch {
                            if (uri == null) snackbarHostState.showSnackbar("No messages to export.")
                            else startShareIntent(context, uri, "Share labels")
                        }
                    }
                },
                onExportFull = {
                    viewModel.exportFullClassificationData { uri ->
                        coroutineScope.launch {
                            if (uri == null) snackbarHostState.showSnackbar("Nothing to export.")
                            else startShareIntent(context, uri, "Share full classification data")
                        }
                    }
                },
                onExportLogs = {
                    viewModel.exportMisclassificationLogs { uri ->
                        coroutineScope.launch {
                            if (uri == null) snackbarHostState.showSnackbar("No reports to export.")
                            else startShareIntent(context, uri, "Share misclassification logs")
                        }
                    }
                }
            )

            // === Section: Diagnostics ===
            DiagnosticsSection(
                isDefaultSms = isDefaultSms,
                providerAuthority = viewModel.getProviderAuthority(),
                packageName = context.packageName
            )

            // === Section: Feedback ===
            SettingsSection(title = "Feedback") {
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
            }

            Spacer(modifier = Modifier.height(8.dp))
        }
    }
}

// =============================================================================
// === Reusable section primitives
// =============================================================================

@Composable
private fun SettingsSection(
    title: String,
    content: @Composable ColumnScope.() -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            text = title.uppercase(),
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.padding(start = 6.dp)
        )
        Surface(
            shape = RoundedCornerShape(18.dp),
            color = MaterialTheme.colorScheme.surface,
            tonalElevation = 1.dp,
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier.padding(vertical = 4.dp),
                content = content
            )
        }
    }
}

@Composable
private fun SettingsRow(
    icon: ImageVector,
    title: String,
    subtitle: String? = null,
    trailing: @Composable (() -> Unit)? = null
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(36.dp)
                .clip(CircleShape)
                .background(MaterialTheme.colorScheme.primaryContainer),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(20.dp)
            )
        }
        Spacer(modifier = Modifier.width(14.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.Medium
            )
            if (subtitle != null) {
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
        if (trailing != null) {
            Spacer(modifier = Modifier.width(8.dp))
            trailing()
        }
    }
}

@Composable
private fun SectionDivider() {
    Divider(
        modifier = Modifier.padding(start = 66.dp),
        color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f),
        thickness = 0.5.dp
    )
}

// =============================================================================
// === Sections
// =============================================================================

@Composable
private fun BackendSection(viewModel: SettingsViewModel) {
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
                    TextButton(onClick = { viewModel.checkBackendHealth() }) {
                        Text("Check")
                    }
                }
            }
        )
    }
}

@Composable
private fun PerformanceSection(viewModel: SettingsViewModel) {
    val performanceStats by viewModel.performanceStats.collectAsState()

    SettingsSection(title = "Performance") {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.primaryContainer),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Speed,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(20.dp)
                )
            }
            Spacer(modifier = Modifier.width(14.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text("Latency stats", style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Medium)
                val stats = performanceStats
                if (stats == null || stats.totalRequests <= 0) {
                    Text(
                        text = "No data yet",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else {
                    Text(
                        text = "${stats.totalRequests} reqs · avg ${stats.averageLatency}ms · " +
                            "min ${stats.minLatency}ms · max ${stats.maxLatency}ms",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            TextButton(onClick = { viewModel.refreshPerformanceStats() }) { Text("Refresh") }
            if ((performanceStats?.totalRequests ?: 0) > 0) {
                TextButton(onClick = {
                    viewModel.clearPerformanceStats()
                    viewModel.refreshPerformanceStats()
                }) { Text("Clear") }
            }
        }
    }
}

@Composable
private fun NotificationsSection(
    areNotificationsEnabled: Boolean,
    soundEnabled: Boolean,
    vibrationEnabled: Boolean,
    onSoundChange: (Boolean) -> Unit,
    onVibrationChange: (Boolean) -> Unit,
    onOpenAppNotifs: () -> Unit,
    onOpenChannelNotifs: () -> Unit
) {
    SettingsSection(title = "Notifications") {
        SettingsRow(
            icon = Icons.Default.Notifications,
            title = "System notifications",
            subtitle = if (areNotificationsEnabled) "Enabled in system settings"
            else "Disabled in system settings",
            trailing = if (!areNotificationsEnabled) {
                { FilledTonalButton(onClick = onOpenAppNotifs) { Text("Enable") } }
            } else null
        )
        SectionDivider()
        ToggleRow(
            title = "Notification sound",
            subtitle = "Play sound for incoming SMS",
            checked = soundEnabled,
            onCheckedChange = onSoundChange
        )
        SectionDivider()
        ToggleRow(
            title = "Vibration",
            subtitle = "Vibrate for incoming SMS",
            checked = vibrationEnabled,
            onCheckedChange = onVibrationChange
        )
        SectionDivider()
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            OutlinedButton(
                onClick = onOpenAppNotifs,
                modifier = Modifier.weight(1f)
            ) { Text("App notifications") }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                OutlinedButton(
                    onClick = onOpenChannelNotifs,
                    modifier = Modifier.weight(1f)
                ) { Text("Channels") }
            }
        }
    }
}

@Composable
private fun ToggleRow(
    title: String,
    subtitle: String?,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Spacer(modifier = Modifier.width(50.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.bodyLarge)
            if (subtitle != null) {
                Text(
                    subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
        Switch(checked = checked, onCheckedChange = onCheckedChange)
    }
}

@Composable
private fun ExportSection(
    onExportLabels: () -> Unit,
    onExportFull: () -> Unit,
    onExportLogs: () -> Unit
) {
    SettingsSection(title = "Export data") {
        SettingsRow(
            icon = Icons.Default.FileDownload,
            title = "Full classification data",
            subtitle = "All messages, predictions, reasons, and your reports — share with the developer to debug misclassifications.",
            trailing = {
                FilledTonalButton(onClick = onExportFull) { Text("Export") }
            }
        )
        SectionDivider()
        SettingsRow(
            icon = Icons.Default.Description,
            title = "Labels only",
            subtitle = "Compact CSV with sender, body, and label",
            trailing = {
                TextButton(onClick = onExportLabels) { Text("Export") }
            }
        )
        SectionDivider()
        SettingsRow(
            icon = Icons.Default.BugReport,
            title = "Misclassification reports",
            subtitle = "Only your tagged misclassifications",
            trailing = {
                TextButton(onClick = onExportLogs) { Text("Export") }
            }
        )
    }
}

@Composable
private fun DiagnosticsSection(
    isDefaultSms: Boolean,
    providerAuthority: String,
    packageName: String
) {
    var expanded by remember { mutableStateOf(false) }
    SettingsSection(title = "Diagnostics") {
        SettingsRow(
            icon = Icons.Default.Settings,
            title = "Debug info",
            subtitle = if (expanded) "Tap to hide" else "Tap to view technical details for OTP autofill troubleshooting",
            trailing = {
                TextButton(onClick = { expanded = !expanded }) {
                    Text(if (expanded) "Hide" else "Show")
                }
            }
        )
        if (expanded) {
            Column(
                modifier = Modifier.padding(start = 66.dp, end = 16.dp, bottom = 14.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                DiagLine("Default SMS handler", if (isDefaultSms) "Yes" else "No")
                DiagLine("Provider authority", providerAuthority)
                DiagLine("Package", packageName)
                Text(
                    text = "OTP-aware apps query content://sms/inbox via the system Telephony provider. " +
                        "When this app is the default SMS handler, we mirror every incoming SMS into the " +
                        "system provider so other apps can read OTPs.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 6.dp)
                )
            }
        }
    }
}

@Composable
private fun DiagLine(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth()) {
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

private fun startShareIntent(context: Context, uri: Uri, title: String) {
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "text/csv"
        putExtra(Intent.EXTRA_STREAM, uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    context.startActivity(Intent.createChooser(intent, title))
}

private fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is android.content.ContextWrapper -> baseContext.findActivity()
    else -> null
}
