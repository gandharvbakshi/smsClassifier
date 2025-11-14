package com.smsclassifier.app.ui.screens

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.ui.viewmodel.InferenceMode
import com.smsclassifier.app.ui.viewmodel.SettingsViewModel

@Composable
fun SettingsScreen(
    viewModel: SettingsViewModel,
    modifier: Modifier = Modifier
) {
    val inferenceMode by viewModel.inferenceMode.collectAsState()
    val isDefaultSms by viewModel.isDefaultSmsApp.collectAsState()
    val context = LocalContext.current
    val activity = remember(context) { context.findActivity() }

    LaunchedEffect(Unit) {
        viewModel.refreshDefaultSmsStatus()
    }

    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) {
        viewModel.refreshDefaultSmsStatus()
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            text = "Settings",
            style = MaterialTheme.typography.headlineMedium
        )
        
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
                
                InferenceMode.values().forEach { mode ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(mode.name)
                        RadioButton(
                            selected = inferenceMode == mode,
                            onClick = { viewModel.setInferenceMode(mode) }
                        )
                    }
                }
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
        
        // Export Labels (placeholder)
        Button(
            onClick = { /* TODO: export labels */ },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Export Labels")
        }
    }
}

private fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is android.content.ContextWrapper -> baseContext.findActivity()
    else -> null
}

