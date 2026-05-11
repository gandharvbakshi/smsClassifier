package com.smsclassifier.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.BugReport
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.BuildConfig
import com.smsclassifier.app.ui.viewmodel.SettingsViewModel
import androidx.compose.runtime.collectAsState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DiagnosticsSubScreen(
    viewModel: SettingsViewModel,
    onBack: () -> Unit,
    onOpenNotificationDebug: () -> Unit
) {
    val context = LocalContext.current
    val isDefaultSms by viewModel.isDefaultSmsApp.collectAsState()

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("Diagnostics & self-test", fontWeight = FontWeight.SemiBold) },
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
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            PerformanceSectionContent(viewModel)
            OtpSelfTestSectionContent(viewModel)
            DiagnosticsSectionContent(
                isDefaultSms = isDefaultSms,
                providerAuthority = viewModel.getProviderAuthority(),
                packageName = context.packageName
            )
            if (BuildConfig.DEBUG) {
                SettingsSection(title = "Debug") {
                    ListItem(
                        headlineContent = { Text("Notification debug") },
                        supportingContent = {
                            Text(
                                "See exactly what the system OTP-autofill scraper saw for each " +
                                    "notification we posted."
                            )
                        },
                        leadingContent = { Icon(Icons.Default.BugReport, contentDescription = null) },
                        modifier = Modifier.clickable { onOpenNotificationDebug() }
                    )
                }
            }
        }
    }
}

@Composable
internal fun PerformanceSectionContent(viewModel: SettingsViewModel) {
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
            IconButton(onClick = { viewModel.refreshPerformanceStats() }) {
                Icon(Icons.Default.Refresh, contentDescription = "Refresh stats")
            }
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
internal fun OtpSelfTestSectionContent(viewModel: SettingsViewModel) {
    val result by viewModel.otpSelfTest.collectAsState()
    val running by viewModel.isRunningSelfTest.collectAsState()

    SettingsSection(title = "OTP autofill self-test") {
        SettingsRow(
            icon = Icons.Default.BugReport,
            title = "Verify OTP plumbing",
            subtitle = if (result == null)
                "Confirms that other apps (Swiggy/Amazon/etc.) can actually read SMS we receive."
            else "Last result below — re-run after receiving an OTP.",
            trailing = {
                if (running) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        strokeWidth = 2.dp
                    )
                } else {
                    FilledTonalButton(onClick = { viewModel.runOtpSelfTest() }) {
                        Text(if (result == null) "Run" else "Re-run")
                    }
                }
            }
        )
        result?.let { r ->
            Column(
                modifier = Modifier.padding(start = 66.dp, end = 16.dp, bottom = 14.dp),
                verticalArrangement = Arrangement.spacedBy(2.dp)
            ) {
                CheckLine("Default SMS app", r.isDefaultSms,
                    okText = "Yes", failText = "No (other apps will see nothing)")
                CheckLine("Can query system inbox", r.canQueryInbox,
                    okText = "Yes", failText = "No — READ_SMS denied?")
                CheckLine("Can write to system inbox", r.canInsertProbe,
                    okText = "Probe row inserted & deleted",
                    failText = "Insert returned null — OEM rejecting writes")
                DiagLine(
                    "Inbox rows: system vs ours",
                    "${r.systemInboxCount} / ${r.ourDbCount}"
                )
                DiagLine(
                    "Default SMS subscription id",
                    if (r.defaultSmsSubId >= 0) r.defaultSmsSubId.toString() else "missing"
                )
                DiagLine(
                    "Active SIM subscription ids",
                    if (r.activeSubIds.isEmpty()) "(none reported)"
                    else r.activeSubIds.joinToString()
                )
                DiagLine(
                    "Latest inbox row has SUBSCRIPTION_ID",
                    when (r.latestRowHasSubId) {
                        true -> "Yes ✓"
                        false -> "MISSING — autofill will be blocked on dual SIM"
                        null -> "—"
                    }
                )
                DiagLine(
                    "Latest inbox row has PROTOCOL",
                    when (r.latestRowHasProtocol) {
                        true -> "Yes ✓"
                        false -> "missing"
                        null -> "—"
                    }
                )
                r.latestSystemInboxTs?.let {
                    DiagLine("Latest inbox row date", java.text.SimpleDateFormat(
                        "MMM d, h:mm a", java.util.Locale.getDefault()
                    ).format(java.util.Date(it)))
                }
                r.errorMessage?.let {
                    Text(
                        text = it,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier.padding(top = 4.dp)
                    )
                }
                Text(
                    text = "How to read this: if 'system inbox rows' is much smaller than 'ours', " +
                        "or 'SUBSCRIPTION_ID missing' shows up, that's why Swiggy/Amazon don't see " +
                        "OTPs. Receive a fresh OTP after installing v1.0.10 then re-run.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 6.dp)
                )
            }
        }
    }
}

@Composable
internal fun DiagnosticsSectionContent(
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
