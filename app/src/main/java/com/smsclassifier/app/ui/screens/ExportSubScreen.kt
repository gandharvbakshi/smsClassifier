package com.smsclassifier.app.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.BugReport
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.FileDownload
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.ui.viewmodel.SettingsViewModel
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ExportSubScreen(
    viewModel: SettingsViewModel,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    val exportError by viewModel.lastExportError.collectAsState()
    LaunchedEffect(exportError) {
        exportError?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.consumeExportError()
        }
    }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("Export my data", fontWeight = FontWeight.SemiBold) },
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
                .padding(horizontal = 16.dp, vertical = 12.dp)
        ) {
            SettingsSection(title = "Exports") {
                SettingsRow(
                    icon = Icons.Default.FileDownload,
                    title = "Full classification data",
                    subtitle = "All messages, predictions, reasons, and your reports.",
                    trailing = {
                        FilledTonalButton(onClick = {
                            viewModel.exportFullClassificationData { uri ->
                                scope.launch {
                                    if (uri == null) snackbarHostState.showSnackbar("Nothing to export.")
                                    else startShareIntent(context, uri, "Share full classification data")
                                }
                            }
                        }) { Text("Export") }
                    }
                )
                SectionDivider()
                SettingsRow(
                    icon = Icons.Default.Description,
                    title = "Labels only",
                    subtitle = "Compact CSV with sender, body, and label",
                    trailing = {
                        TextButton(onClick = {
                            viewModel.exportLabels { uri ->
                                scope.launch {
                                    if (uri == null) snackbarHostState.showSnackbar("No messages to export.")
                                    else startShareIntent(context, uri, "Share labels")
                                }
                            }
                        }) { Text("Export") }
                    }
                )
                SectionDivider()
                SettingsRow(
                    icon = Icons.Default.BugReport,
                    title = "Misclassification reports",
                    subtitle = "Only your tagged misclassifications",
                    trailing = {
                        TextButton(onClick = {
                            viewModel.exportMisclassificationLogs { uri ->
                                scope.launch {
                                    if (uri == null) snackbarHostState.showSnackbar("No reports to export.")
                                    else startShareIntent(context, uri, "Share misclassification logs")
                                }
                            }
                        }) { Text("Export") }
                    }
                )
            }
        }
    }
}
