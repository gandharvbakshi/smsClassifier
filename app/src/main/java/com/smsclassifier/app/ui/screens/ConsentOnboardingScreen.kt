package com.smsclassifier.app.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.R
import com.smsclassifier.app.analytics.Telemetry
import kotlinx.coroutines.launch
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ListItem

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConsentOnboardingScreen(onContinue: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val consent = AppContainer.consentManager

    var analyticsOn by remember { mutableStateOf(false) }
    var crashOn by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "Welcome to SMS Classifier",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.SemiBold
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = "Choose what you are comfortable sharing. You can change this anytime in Settings.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.height(24.dp))
        ConsentToggleRow(
            title = "Anonymous usage analytics",
            subtitle = "Helps us see which features are used (no message content).",
            checked = analyticsOn,
            onCheckedChange = { analyticsOn = it }
        )
        Spacer(modifier = Modifier.height(12.dp))
        ConsentToggleRow(
            title = "Crash reports",
            subtitle = "Helps us fix bugs. No message text is included.",
            checked = crashOn,
            onCheckedChange = { crashOn = it }
        )
        Spacer(modifier = Modifier.height(24.dp))
        TextButton(
            onClick = {
                val url = context.getString(R.string.privacy_policy_url)
                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            }
        ) { Text("Privacy policy") }
        Spacer(modifier = Modifier.height(16.dp))
        Button(
            onClick = {
                scope.launch {
                    consent.setAnalyticsConsent(analyticsOn)
                    consent.setCrashlyticsConsent(crashOn)
                    consent.markOnboardingConsentSeen()
                    val launchPrefs = context.getSharedPreferences(
                        "telemetry_launch",
                        android.content.Context.MODE_PRIVATE
                    )
                    val alreadyLogged = launchPrefs.getBoolean("logged_app_first_open", false)
                    launchPrefs.edit()
                        .putLong("first_open_at_ms", System.currentTimeMillis())
                        .putBoolean("logged_app_first_open", true)
                        .apply()
                    if (!alreadyLogged) {
                        Telemetry.instance?.logEvent("app_first_open")
                    }
                    onContinue()
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) { Text("Continue") }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ConsentToggleRow(
    title: String,
    subtitle: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    Column(modifier = Modifier.fillMaxWidth()) {
        ListItem(
            headlineContent = { Text(title, fontWeight = FontWeight.Medium) },
            supportingContent = { Text(subtitle, style = MaterialTheme.typography.bodySmall) },
            trailingContent = {
                Switch(checked = checked, onCheckedChange = onCheckedChange)
            }
        )
    }
}
