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
import androidx.compose.material.icons.filled.PrivacyTip
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
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
    onUnlockPro: () -> Unit,
    onSetDefaultSms: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val consent = AppContainer.consentManager
    val entitlementManager = AppContainer.entitlementManager
    var entitlementState by remember { mutableStateOf(entitlementManager.currentState()) }
    var entitlementRefresh by remember { mutableStateOf(0) }
    val trialDaysRemaining = remember(entitlementRefresh, entitlementState) { entitlementManager.trialDaysRemaining() }
    val trialLabel = remember(entitlementRefresh, entitlementState) { entitlementManager.trialDurationLabel() }
    val onboardingAlreadySeen = remember { consent.onboardingSeenNow() }

    var analyticsOn by rememberSaveable {
        mutableStateOf(if (onboardingAlreadySeen) consent.analyticsEnabledNow() else true)
    }
    var crashOn by rememberSaveable {
        mutableStateOf(if (onboardingAlreadySeen) consent.crashlyticsEnabledNow() else true)
    }

    LaunchedEffect(Unit) {
        if (entitlementManager.refreshFromServer()) {
            entitlementRefresh++
            entitlementState = entitlementManager.currentState()
        }
    }

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
                text = "Find OTPs and spot risky messages",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = "This app shows your texts, makes OTPs easy to copy, and warns you about scams.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface
            )

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
                    text = "Privacy and diagnostics",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = stringResource(R.string.privacy_cloud_checks_summary),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                ConsentToggleRow(
                    title = "Usage diagnostics",
                    subtitle = "Share feature usage only. Message content is not included.",
                    checked = analyticsOn,
                    onCheckedChange = { analyticsOn = it }
                )
                ConsentToggleRow(
                    title = "Crash reports",
                    subtitle = "Helps fix bugs. Message text is not included.",
                    checked = crashOn,
                    onCheckedChange = { crashOn = it }
                )
                SecondaryButton(
                    text = "Read privacy policy",
                    onClick = {
                        val url = context.getString(R.string.privacy_policy_url)
                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                    }
                )
            }

            InfoCard {
                Text(
                    text = "Make this your SMS app",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = "Set it as the default SMS app so it can import existing SMS on this phone, sort new messages, and show OTP alerts.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                SecondaryButton(
                    text = "Set as default SMS app",
                    onClick = onSetDefaultSms
                )
            }

            InfoCard {
                Text(
                    text = "Choose your mode",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = "Free sorts messages on this phone. Pro adds cloud scam warnings, OTP purpose, and 'Do not share' alerts. You can try Pro for $trialLabel from the Pro screen.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                PrimaryButton(
                    text = if (entitlementState == EntitlementState.PRO) {
                        "Open app"
                    } else {
                        "Start free - I'll explore Pro later"
                    },
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
                    text = "See Pro features",
                    onClick = {
                        scope.launch {
                            persistConsent(
                                context = context,
                                consent = consent,
                                analyticsOn = analyticsOn,
                                crashOn = crashOn
                            )
                            AppContainer.telemetry.logCtaTap("onboarding", "see_pro_features")
                            onUnlockPro()
                        }
                    }
                )
            }
        }
    }
}

@Composable
private fun ConsentToggleRow(
    title: String,
    subtitle: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(Spacing.md),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange
        )
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
