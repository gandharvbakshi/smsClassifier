package com.smsclassifier.app.ui.screens

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.PrivacyTip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
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

@Composable
fun ConsentOnboardingScreen(
    isDefaultSmsApp: Boolean,
    onContinueBasic: () -> Unit,
    onStartProTrial: suspend () -> Boolean,
    onContinueToInbox: () -> Unit,
    onSetDefaultSms: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val consent = AppContainer.consentManager
    val entitlementManager = AppContainer.entitlementManager
    var step by rememberSaveable { mutableStateOf(0) }
    var entitlementState by remember { mutableStateOf(entitlementManager.currentState()) }
    var entitlementRefresh by remember { mutableStateOf(0) }
    val trialDaysRemaining = remember(entitlementRefresh, entitlementState) {
        entitlementManager.trialDaysRemaining()
    }
    val trialLabel = remember(entitlementRefresh, entitlementState) {
        entitlementManager.trialDurationLabel()
    }
    val onboardingAlreadySeen = remember { consent.onboardingSeenNow() }

    var analyticsOn by rememberSaveable {
        mutableStateOf(if (onboardingAlreadySeen) consent.analyticsEnabledNow() else true)
    }
    var crashOn by rememberSaveable {
        mutableStateOf(if (onboardingAlreadySeen) consent.crashlyticsEnabledNow() else true)
    }
    var trialStartInFlight by rememberSaveable { mutableStateOf(false) }
    var trialStartError by rememberSaveable { mutableStateOf<String?>(null) }

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
        ) {
            Column(
                modifier = Modifier
                    .weight(1f)
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = Spacing.xl, vertical = Spacing.lg),
                verticalArrangement = Arrangement.spacedBy(Spacing.lg),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                StepProgress(step = step)

                when (step) {
                    0 -> WelcomeStep()
                    1 -> PrivacyStep(
                        context = context,
                        analyticsOn = analyticsOn,
                        crashOn = crashOn,
                        onAnalyticsChange = { analyticsOn = it },
                        onCrashChange = { crashOn = it }
                    )
                    2 -> DefaultSmsStep(
                        isDefaultSmsApp = isDefaultSmsApp,
                        onSetDefaultSms = onSetDefaultSms
                    )
                    else -> ProStep(
                        entitlementState = entitlementState,
                        trialDaysRemaining = trialDaysRemaining,
                        trialLabel = trialLabel,
                        trialStartError = trialStartError
                    )
                }
            }

            Surface(
                color = MaterialTheme.colorScheme.surface,
                tonalElevation = 1.dp,
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = Spacing.xl, vertical = Spacing.md),
                    verticalArrangement = Arrangement.spacedBy(Spacing.sm)
                ) {
                    if (step < 3) {
                        PrimaryButton(
                            text = "Continue",
                            onClick = { step++ },
                            enabled = step != 2 || isDefaultSmsApp
                        )
                    } else {
                        PrimaryButton(
                            text = when {
                                entitlementState == EntitlementState.PRO ||
                                    entitlementState == EntitlementState.TRIAL_ACTIVE -> "Open app"
                                trialStartInFlight -> "Starting Pro trial..."
                                else -> "Start 14-day free trial"
                            },
                            onClick = {
                                scope.launch {
                                    trialStartError = null
                                    if (
                                        entitlementState != EntitlementState.PRO &&
                                        entitlementState != EntitlementState.TRIAL_ACTIVE
                                    ) {
                                        trialStartInFlight = true
                                        val started = onStartProTrial()
                                        trialStartInFlight = false
                                        if (!started) {
                                            trialStartError =
                                                "Could not start Pro trial. Check internet and try again, or use the app without Pro for now."
                                            return@launch
                                        }
                                    }
                                    persistConsent(
                                        context = context,
                                        consent = consent,
                                        analyticsOn = analyticsOn,
                                        crashOn = crashOn
                                    )
                                    AppContainer.telemetry.logCtaTap("onboarding", "start_pro_trial")
                                    onContinueToInbox()
                                }
                            },
                            enabled = !trialStartInFlight
                        )
                    }

                    if (
                        step == 3 &&
                        entitlementState != EntitlementState.PRO &&
                        entitlementState != EntitlementState.TRIAL_ACTIVE
                    ) {
                        SecondaryButton(
                            text = "Use app without Pro",
                            onClick = {
                                scope.launch {
                                    persistConsent(
                                        context = context,
                                        consent = consent,
                                        analyticsOn = analyticsOn,
                                        crashOn = crashOn
                                    )
                                    AppContainer.telemetry.logCtaTap("onboarding", "continue_basic")
                                    onContinueBasic()
                                }
                            },
                            enabled = !trialStartInFlight
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun StepProgress(step: Int) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm)
    ) {
        Text(
            text = "Step ${step + 1} of 4",
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            fontWeight = FontWeight.SemiBold
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            repeat(4) { index ->
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .height(6.dp)
                        .clip(RoundedCornerShape(100.dp))
                        .background(
                            if (index <= step) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                MaterialTheme.colorScheme.surfaceVariant
                            }
                        )
                )
            }
        }
    }
}

@Composable
private fun WelcomeStep() {
    HeroIcon(
        icon = Icons.Default.PrivacyTip,
        modifier = Modifier.padding(top = Spacing.sm)
    )
    Text(
        text = "Find OTPs and spot risky texts",
        style = MaterialTheme.typography.headlineMedium,
        fontWeight = FontWeight.Bold,
        textAlign = TextAlign.Center
    )
    Text(
        text = "SMS Classifier sorts your texts, highlights OTPs, and warns you when a message looks unsafe.",
        style = MaterialTheme.typography.bodyLarge,
        color = MaterialTheme.colorScheme.onSurface,
        textAlign = TextAlign.Center
    )
    InfoCard {
        Text(
            text = "What you get",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.SemiBold
        )
        SimpleBullet("OTPs are easier to find and copy.")
        SimpleBullet("Risky links and payment requests stand out.")
        SimpleBullet("You can report mistakes when the app gets a label wrong.")
    }
}

@Composable
private fun PrivacyStep(
    context: Context,
    analyticsOn: Boolean,
    crashOn: Boolean,
    onAnalyticsChange: (Boolean) -> Unit,
    onCrashChange: (Boolean) -> Unit
) {
    Text(
        text = "Privacy and diagnostics",
        style = MaterialTheme.typography.headlineSmall,
        fontWeight = FontWeight.Bold,
        textAlign = TextAlign.Center,
        modifier = Modifier.fillMaxWidth()
    )
    Text(
        text = "Diagnostics are on to help us fix problems. They never include message content.",
        style = MaterialTheme.typography.bodyLarge,
        color = MaterialTheme.colorScheme.onSurface,
        textAlign = TextAlign.Center
    )
    InfoCard {
        Text(
            text = "Help improve the app",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.SemiBold
        )
        Text(
            text = "These are on to help us find bugs. You can turn either off now or later in Settings.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        ConsentToggleRow(
            title = "Usage diagnostics",
            subtitle = "Feature usage only. Message content is not included.",
            checked = analyticsOn,
            onCheckedChange = onAnalyticsChange
        )
        ConsentToggleRow(
            title = "Crash reports",
            subtitle = "Crash details only. Message text is not included.",
            checked = crashOn,
            onCheckedChange = onCrashChange
        )
        SecondaryButton(
            text = "Read privacy policy",
            onClick = {
                val url = context.getString(R.string.privacy_policy_url)
                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            }
        )
    }
}

@Composable
private fun DefaultSmsStep(
    isDefaultSmsApp: Boolean,
    onSetDefaultSms: () -> Unit
) {
    Text(
        text = "Make this your texting app",
        style = MaterialTheme.typography.headlineSmall,
        fontWeight = FontWeight.Bold,
        textAlign = TextAlign.Center,
        modifier = Modifier.fillMaxWidth()
    )
    Text(
        text = "This lets SMS Classifier import your texts and sort new messages.",
        style = MaterialTheme.typography.bodyLarge,
        color = MaterialTheme.colorScheme.onSurface,
        textAlign = TextAlign.Center
    )
    InfoCard {
        Text(
            text = if (isDefaultSmsApp) "SMS Classifier is your texting app" else "Set as default SMS app",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.SemiBold
        )
        Text(
            text = if (isDefaultSmsApp) {
                "Done. Continue to choose how you want to start."
            } else {
                "Android will ask you to confirm. Come back here after you choose SMS Classifier."
            },
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        if (isDefaultSmsApp) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                verticalAlignment = Alignment.CenterVertically
            ) {
                androidx.compose.material3.Icon(
                    imageVector = Icons.Default.CheckCircle,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(22.dp)
                )
                Text(
                    text = "Ready",
                    style = MaterialTheme.typography.titleSmall,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.SemiBold
                )
            }
        } else {
            SecondaryButton(
                text = "Set as default SMS app",
                onClick = onSetDefaultSms
            )
            Text(
                text = "Continue turns on after Android confirms this step.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun ProStep(
    entitlementState: EntitlementState,
    trialDaysRemaining: Int,
    trialLabel: String,
    trialStartError: String?
) {
    Text(
        text = "Choose how to start",
        style = MaterialTheme.typography.headlineSmall,
        fontWeight = FontWeight.Bold,
        textAlign = TextAlign.Center,
        modifier = Modifier.fillMaxWidth()
    )
    Text(
        text = "We recommend Pro protection first. It is free for $trialLabel and needs no payment method.",
        style = MaterialTheme.typography.bodyLarge,
        color = MaterialTheme.colorScheme.onSurface,
        textAlign = TextAlign.Center
    )
    InfoCard {
        Text(
            text = "Pro protection",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.SemiBold
        )
        Text(
            text = "Scam warnings, OTP purpose, and do-not-share alerts are included.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(
            text = "Cloud checks send message text and sender securely to our server only when Pro classification is used.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        if (entitlementState == EntitlementState.PRO || entitlementState == EntitlementState.TRIAL_ACTIVE) {
            Text(
                text = when (entitlementState) {
                    EntitlementState.PRO -> "Pro is already active on this phone."
                    EntitlementState.TRIAL_ACTIVE -> "Trial active: $trialDaysRemaining day(s) remaining."
                    else -> ""
                },
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.SemiBold
            )
        }
        trialStartError?.let { error ->
            Text(
                text = error,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.error
            )
        }
    }
}

@Composable
private fun SimpleBullet(text: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        verticalAlignment = Alignment.Top
    ) {
        Box(
            modifier = Modifier
                .padding(top = 8.dp)
                .size(6.dp)
                .clip(RoundedCornerShape(100.dp))
                .background(MaterialTheme.colorScheme.primary)
        )
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.weight(1f)
        )
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
    Telemetry.instance?.logEvent("onboarding_complete")
}
