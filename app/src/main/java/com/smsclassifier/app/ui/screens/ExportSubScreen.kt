package com.smsclassifier.app.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
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
import com.smsclassifier.app.BuildConfig
import com.smsclassifier.app.ui.viewmodel.SettingsViewModel
import kotlinx.coroutines.launch

private fun startZipShareIntent(context: android.content.Context, uri: Uri, title: String) {
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "application/zip"
        putExtra(Intent.EXTRA_STREAM, uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    context.startActivity(Intent.createChooser(intent, title))
}

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
                FilledTonalButton(
                    onClick = {
                        scope.launch {
                            viewModel.exportAllToZip { uri ->
                                scope.launch {
                                    if (uri == null) {
                                        snackbarHostState.showSnackbar("Export failed.")
                                    } else {
                                        startZipShareIntent(context, uri, "Share your data")
                                    }
                                }
                            }
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 12.dp)
                ) { Text("Export my data") }

                if (BuildConfig.DEBUG) {
                    SectionDivider()
                    SettingsRow(
                        icon = Icons.Default.FileDownload,
                        title = "Full classification data",
                        subtitle = "All messages with tags, reasons, and notes you added.",
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
                        subtitle = "Smaller table: sender, body, and label only.",
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
                        subtitle = "Only messages you marked as wrong.",
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
}
