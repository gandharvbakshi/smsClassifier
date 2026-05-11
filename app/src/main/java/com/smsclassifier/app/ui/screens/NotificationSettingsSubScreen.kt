package com.smsclassifier.app.ui.screens

import android.os.Build
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.app.NotificationManagerCompat
import com.smsclassifier.app.ui.viewmodel.SettingsViewModel
import androidx.compose.ui.platform.LocalContext
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NotificationSettingsSubScreen(
    viewModel: SettingsViewModel,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val areNotificationsEnabled = remember {
        NotificationManagerCompat.from(context).areNotificationsEnabled()
    }
    var soundEnabled by remember { mutableStateOf(viewModel.notificationSoundEnabled) }
    var vibrationEnabled by remember { mutableStateOf(viewModel.notificationVibrationEnabled) }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("Notifications", fontWeight = FontWeight.SemiBold) },
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
            SettingsSection(title = "Notifications") {
                SettingsRow(
                    icon = Icons.Default.Notifications,
                    title = "System notifications",
                    subtitle = if (areNotificationsEnabled) "Enabled in system settings"
                    else "Disabled in system settings",
                    trailing = if (!areNotificationsEnabled) {
                        { FilledTonalButton(onClick = { viewModel.openNotificationSettings() }) { Text("Enable") } }
                    } else null
                )
                SectionDivider()
                ToggleRow(
                    title = "Notification sound",
                    subtitle = "Play sound for incoming SMS",
                    checked = soundEnabled,
                    onCheckedChange = {
                        soundEnabled = it
                        viewModel.setNotificationSoundEnabled(it)
                    }
                )
                SectionDivider()
                ToggleRow(
                    title = "Vibration",
                    subtitle = "Vibrate for incoming SMS",
                    checked = vibrationEnabled,
                    onCheckedChange = {
                        vibrationEnabled = it
                        viewModel.setNotificationVibrationEnabled(it)
                    }
                )
                SectionDivider()
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedButton(
                        onClick = { viewModel.openNotificationSettings() },
                        modifier = Modifier.weight(1f)
                    ) { Text("App notifications") }
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        OutlinedButton(
                            onClick = { viewModel.openNotificationChannelSettings() },
                            modifier = Modifier.weight(1f).padding(start = 8.dp)
                        ) { Text("Channels") }
                    }
                }
            }
        }
    }
}
