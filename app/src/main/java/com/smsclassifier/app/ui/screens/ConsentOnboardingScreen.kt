package com.smsclassifier.app.ui.screens

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Divider
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.R
import com.smsclassifier.app.analytics.Telemetry
import com.smsclassifier.app.entitlement.EntitlementState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CloudUpload
import androidx.compose.material.icons.filled.Inbox
import androidx.compose.material.icons.filled.PrivacyTip
import androidx.compose.material.icons.filled.Star
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConsentOnboardingScreen(
    onContinueFree: () -> Unit,
    onUnlockPro: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val consent = AppContainer.consentManager
    val entitlementManager = AppContainer.entitlementManager
    var entitlementState by remember { mutableStateOf(entitlementManager.currentState()) }
    val trialDaysRemaining = remember { entitlementManager.trialDaysRemaining() }
    val trialAvailable = !entitlementManager.hasTrialStarted()
    val onboardingAlreadySeen = remember { consent.onboardingSeenNow() }

    var analyticsOn by rememberSaveable {
        mutableStateOf(if (onboardingAlreadySeen) consent.analyticsEnabledNow() else true)
    }
    var crashOn by rememberSaveable { mutableStateOf(consent.crashlyticsEnabledNow()) }
    var privacySaved by rememberSaveable { mutableStateOf(onboardingAlreadySeen) }
    var trialStartFailed by rememberSaveable { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 12.dp),
            contentAlignment = Alignment.Center
        ) {
            Surface(
                shape = androidx.compose.foundation.shape.CircleShape,
                color = MaterialTheme.colorScheme.primaryContainer
            ) {
                Icon(
                    imageVector = Icons.Default.PrivacyTip,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(18.dp)
                )
            }
        }

        Text(
            text = "Set up SMS Classifier",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.SemiBold
        )
        Text(
            text = "Choose privacy options first, then pick how you want message classification to work.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f)
            )
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    text = "What it helps with",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )
                ExplainerRow(
                    icon = Icons.Default.Inbox,
                    title = "Organized OTP inbox",
                    body = "Keeps codes easier to find without turning every message into an alert."
                )
                ExplainerRow(
                    icon = Icons.Default.CloudUpload,
                    title = "OTP intent in Pro",
                    body = "Explains why a code arrived, such as login, payment, account change, or delivery."
                )
                ExplainerRow(
                    icon = Icons.Default.PrivacyTip,
                    title = "Phishing risk in Pro",
                    body = "Adds warnings for suspicious links, urgency, and requests for passwords or OTPs."
                )
            }
        }
        if (entitlementState == EntitlementState.PRO || entitlementState == EntitlementState.TRIAL_ACTIVE) {
            Text(
                text = when (entitlementState) {
                    EntitlementState.PRO -> "Pro is already active on this install."
                    EntitlementState.TRIAL_ACTIVE -> "Trial active: $trialDaysRemaining day(s) remaining."
                    else -> ""
                },
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.primary
            )
        }

        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f)
            )
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Privacy choices",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = "You can change these later in Settings.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.height(12.dp))
                ConsentToggleRow(
                    title = "Anonymous usage analytics (recommended)",
                    subtitle = "Helps us see what gets used. No message content.",
                    checked = analyticsOn,
                    onCheckedChange = { analyticsOn = it }
                )
                Divider(modifier = Modifier.padding(vertical = 8.dp))
                ConsentToggleRow(
                    title = "Crash reports",
                    subtitle = "Helps us fix bugs. No message text is included.",
                    checked = crashOn,
                    onCheckedChange = { crashOn = it }
                )
                Spacer(modifier = Modifier.height(12.dp))
                TextButton(
                    onClick = {
                        val url = context.getString(R.string.privacy_policy_url)
                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                    }
                ) { Text("Privacy policy") }
                Spacer(modifier = Modifier.height(4.dp))
                Button(
                    onClick = {
                        scope.launch {
                            persistConsent(
                                context = context,
                                consent = consent,
                                analyticsOn = analyticsOn,
                                crashOn = crashOn
                            )
                            AppContainer.telemetry.logCtaTap("onboarding", "save_privacy")
                            privacySaved = true
                        }
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(if (privacySaved) "Privacy saved" else "Save privacy choices")
                }
            }
        }

        if (privacySaved) {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    text = "Choose your mode",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = "Free keeps basic local classification on-device. Trial and Pro add cloud OTP intent, do-not-share warnings, phishing detection, and risk scoring.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                PlanChoiceCard(
                    icon = Icons.Default.Inbox,
                    title = "Continue free",
                    subtitle = "Use the app with local classification only. No cloud processing.",
                    buttonText = if (entitlementState == EntitlementState.PRO) "Open app" else "Continue free",
                    enabled = true,
                    onClick = {
                        scope.launch {
                            persistConsent(
                                context = context,
                                consent = consent,
                                analyticsOn = analyticsOn,
                                crashOn = crashOn
                            )
                            AppContainer.telemetry.logCtaTap("onboarding", "continue_free")
                            onContinueFree()
                        }
                    }
                )

                PlanChoiceCard(
                    icon = Icons.Default.CloudUpload,
                    title = "Start 7-day Pro trial",
                    subtitle = "Turns on cloud OTP intent, phishing warnings, and risk scoring. No payment method, no auto-charge.",
                    buttonText = when (entitlementState) {
                        EntitlementState.TRIAL_ACTIVE -> "Trial already active"
                        EntitlementState.PRO -> "Pro already active"
                        EntitlementState.TRIAL_EXPIRED -> "Trial already used"
                        else -> "Start trial"
                    },
                    enabled = trialAvailable && entitlementState == EntitlementState.FREE,
                    onClick = {
                        scope.launch {
                            persistConsent(
                                context = context,
                                consent = consent,
                                analyticsOn = analyticsOn,
                                crashOn = crashOn
                            )
                            AppContainer.telemetry.logCtaTap("onboarding", "start_trial")
                            if (entitlementManager.startTrialIfAvailableRemote()) {
                                trialStartFailed = false
                                AppContainer.telemetry.logEvent("trial_started_from_onboarding")
                                entitlementState = entitlementManager.currentState()
                                onContinueFree()
                            } else {
                                trialStartFailed = true
                            }
                        }
                    }
                )

                if (trialStartFailed) {
                    Text(
                        text = "Could not start the trial right now. You can continue free and try again from Pro later.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error
                    )
                }

                PlanChoiceCard(
                    icon = Icons.Default.Star,
                    title = "Unlock Pro",
                    subtitle = "One-time purchase for full Pro access after trial or on its own.",
                    buttonText = "Open paywall",
                    enabled = entitlementState != EntitlementState.PRO,
                    onClick = {
                        scope.launch {
                            persistConsent(
                                context = context,
                                consent = consent,
                                analyticsOn = analyticsOn,
                                crashOn = crashOn
                            )
                            AppContainer.telemetry.logCtaTap("onboarding", "unlock_pro")
                            onUnlockPro()
                        }
                    }
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ExplainerRow(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String,
    body: String
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.Top
    ) {
        Surface(
            shape = androidx.compose.foundation.shape.CircleShape,
            color = MaterialTheme.colorScheme.secondaryContainer
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSecondaryContainer,
                modifier = Modifier.padding(8.dp)
            )
        }
        Column(
            modifier = Modifier.padding(start = 12.dp),
            verticalArrangement = Arrangement.spacedBy(2.dp)
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                text = body,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
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

@Composable
private fun PlanChoiceCard(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String,
    subtitle: String,
    buttonText: String,
    enabled: Boolean,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(
                    shape = androidx.compose.foundation.shape.CircleShape,
                    color = MaterialTheme.colorScheme.secondaryContainer
                ) {
                    Icon(
                        imageVector = icon,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onSecondaryContainer,
                        modifier = Modifier.padding(10.dp)
                    )
                }
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.padding(start = 12.dp)
                )
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(modifier = Modifier.height(12.dp))
            OutlinedButton(
                onClick = onClick,
                enabled = enabled,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(buttonText)
            }
        }
    }
}

private suspend fun persistConsent(
    context: Context,
    consent: com.smsclassifier.app.analytics.ConsentManager,
    analyticsOn: Boolean,
    crashOn: Boolean
) {
    consent.setAnalyticsConsent(analyticsOn)
    consent.setCrashlyticsConsent(crashOn)
    consent.markOnboardingConsentSeen()

    val launchPrefs = context.getSharedPreferences("telemetry_launch", Context.MODE_PRIVATE)
    val alreadyLogged = launchPrefs.getBoolean("logged_app_first_open", false)
    launchPrefs.edit()
        .putLong("first_open_at_ms", System.currentTimeMillis())
        .putBoolean("logged_app_first_open", true)
        .apply()
    if (!alreadyLogged) {
        Telemetry.instance?.logEvent("app_first_open")
    }
}
