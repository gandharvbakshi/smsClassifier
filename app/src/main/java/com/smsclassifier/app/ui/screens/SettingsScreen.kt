package com.smsclassifier.app.ui.screens

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
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

    LaunchedEffect(Unit) {
        viewModel.refreshDefaultSmsStatus()
    }

    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) {
        viewModel.refreshDefaultSmsStatus()
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopAppBar(
                title = { Text("Settings") },
                navigationIcon = {
                    TextButton(onClick = onBack) { Text("Back") }
                }
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
        // Inference Mode
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text(
                    text = "Inference Mode",
                    style = MaterialTheme.typography.titleMedium
                )
                Text(
                    text = "Server (fixed)",
                    style = MaterialTheme.typography.bodyMedium
                )
                Text(
                    text = "All SMS are classified through the backend ensemble.",
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text(
                    text = "Default SMS App",
                    style = MaterialTheme.typography.titleMedium
                )
                Text(
                    text = if (isDefaultSms) "This app is the default SMS handler." else "This app is not the default SMS handler.",
                    style = MaterialTheme.typography.bodyMedium
                )
                Button(
                    onClick = {
                        val intent = viewModel.createDefaultSmsIntent()
                        if (intent != null && activity != null) {
                            launcher.launch(intent)
                        }
                    },
                    enabled = !isDefaultSms,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Set as default SMS app")
                }
            }
        }
        
        // Export Labels
        Button(
            onClick = {
                exportLabels(context, viewModel, snackbarHostState, coroutineScope)
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Export Labels")
        }
    }
    }
}

private fun exportLabels(
    context: Context,
    viewModel: SettingsViewModel,
    snackbarHostState: SnackbarHostState,
    coroutineScope: CoroutineScope
) {
    viewModel.exportLabels { uri ->
        coroutineScope.launch {
            if (uri == null) {
                snackbarHostState.showSnackbar("No messages to export.")
            } else {
                startShareIntent(context, uri)
            }
        }
    }
}

private fun startShareIntent(context: Context, uri: Uri) {
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "text/csv"
        putExtra(Intent.EXTRA_STREAM, uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    context.startActivity(Intent.createChooser(intent, "Share labels"))
}

private fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is android.content.ContextWrapper -> baseContext.findActivity()
    else -> null
}

