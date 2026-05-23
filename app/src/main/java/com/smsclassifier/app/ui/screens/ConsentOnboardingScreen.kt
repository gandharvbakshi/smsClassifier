package com.smsclassifier.app.ui.screens

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CloudUpload
import androidx.compose.material.icons.filled.Inbox
import androidx.compose.material.icons.filled.PrivacyTip
import androidx.compose.material3.Divider
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
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
import com.smsclassifier.app.ui.components.AppScaffold
import com.smsclassifier.app.ui.components.HeroIcon
import com.smsclassifier.app.ui.components.InfoCard
import com.smsclassifier.app.ui.components.PrimaryButton
import com.smsclassifier.app.ui.components.SecondaryButton
import com.smsclassifier.app.ui.theme.Spacing
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

    AppScaffold(
        title = "Set up SMS Classifier",
        modifier = Modifier.fillMaxSize()
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = Spacing.xl, vertical = Spacing.xl),
            verticalArrangement = Arrangement.spacedBy(Spacing.lg),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            HeroIcon(
                icon = Icons.Default.PrivacyTip,
                modifier = Modifier.padding(top = Spacing.sm)
            )

            Text(
                text = "Choose privacy, then choose your path",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = "Set privacy preferences first, then continue free, start the 7-day trial, or subscribe to Pro.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface
            )

            InfoCard {
                Text(
                    text = "What it helps with",
                    style = MaterialTheme.typography.titleLarge,
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

            InfoCard {
                Text(
                    text = "Privacy choices",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = "You can change these later in Settings.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                ConsentToggleRow(
                    title = "Anonymous usage analytics (recommended)",
                    subtitle = "Helps us see what gets used. No message content.",
                    checked = analyticsOn,
                    onCheckedChange = { analyticsOn = it }
                )
                Divider()
                ConsentToggleRow(
                    title = "Crash reports",
                    subtitle = "Helps us fix bugs. No message text is included.",
                    checked = crashOn,
                    onCheckedChange = { crashOn = it }
                )
                SecondaryButton(
                    text = "Privacy policy",
                    onClick = {
                        val url = context.getString(R.string.privacy_policy_url)
                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                    }
                )
                PrimaryButton(
                    text = if (privacySaved) "Privacy saved" else "Save privacy choices",
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
                    }
                )
            }

            if (privacySaved) {
                InfoCard {
                    Text(
                        text = "Choose your mode",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        text = "Free keeps basic local classification on-device. Trial and annual Pro add cloud OTP intent, do-not-share warnings, phishing detection, and risk scoring.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )

                    PrimaryButton(
                        text = if (entitlementState == EntitlementState.PRO) "Open app" else "Continue free",
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

                    SecondaryButton(
                        text = when (entitlementState) {
                            EntitlementState.TRIAL_ACTIVE -> "Trial already active"
                            EntitlementState.PRO -> "Pro already active"
                            EntitlementState.TRIAL_EXPIRED -> "Trial already used"
                            else -> "Start 7-day Pro trial"
                        },
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
                        },
                        enabled = trialAvailable && entitlementState == EntitlementState.FREE
                    )

                    if (trialStartFailed) {
                        Text(
                            text = "Could not start the trial right now. You can continue free and try again from Pro later.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.error
                        )
                    }

                    SecondaryButton(
                        text = "Subscribe to Pro",
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
                        },
                        enabled = entitlementState != EntitlementState.PRO
                    )
                }
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
            modifier = Modifier.padding(start = Spacing.md),
            verticalArrangement = Arrangement.spacedBy(Spacing.xs)
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
    ListItem(
        modifier = Modifier.fillMaxWidth(),
        headlineContent = { Text(title, fontWeight = FontWeight.Medium) },
        supportingContent = { Text(subtitle, style = MaterialTheme.typography.bodySmall) },
        trailingContent = {
            Switch(checked = checked, onCheckedChange = onCheckedChange)
        }
    )
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
