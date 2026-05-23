package com.smsclassifier.app.ui.screens

import android.app.Activity
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Button
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
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.BuildConfig
import com.smsclassifier.app.billing.PlayBillingRepository
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
fun PaywallScreen(
    onClose: () -> Unit,
    onPurchaseFinishedNavigateNext: () -> Unit,
    telemetryTrigger: String = "settings",
    modifier: Modifier = Modifier
) {
    val activity = LocalContext.current as Activity
    val productDetails by AppContainer.billingRepository.productDetails.collectAsState(initial = null)
    val annualPriceLabel = PlayBillingRepository.formattedAnnualPrice(productDetails)?.let { "$it/year" } ?: "..."
    val billingInFlight by AppContainer.billingRepository.isLaunchingFlow.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }
    val entitlementManager = AppContainer.entitlementManager
    val scope = rememberCoroutineScope()
    var entitlementRefresh by remember { mutableStateOf(0) }

    LaunchedEffect(Unit) {
        AppContainer.billingRepository.purchaseError.collect { msg ->
            snackbarHostState.showSnackbar(msg)
        }
    }

    LaunchedEffect(Unit) {
        AppContainer.telemetry.logEvent("paywall_shown", mapOf("trigger" to telemetryTrigger))
        AppContainer.billingRepository.querySkuDetails()
        if (entitlementManager.refreshFromServer()) {
            entitlementRefresh++
        }
    }

    LaunchedEffect(Unit) {
        AppContainer.billingRepository.purchaseSuccess.collect {
            onPurchaseFinishedNavigateNext()
        }
    }

    val state = remember(entitlementRefresh) { entitlementManager.currentState() }
    val trialDays = remember(entitlementRefresh) { entitlementManager.trialDaysRemaining() }
    val trialLabel = remember(entitlementRefresh) { entitlementManager.trialDurationLabel() }
    val trialAvailable = remember(entitlementRefresh) { !entitlementManager.hasTrialStarted() }

    AppScaffold(
        title = "SMS Classifier Pro",
        onBack = onClose,
        snackbarHostState = snackbarHostState,
        modifier = modifier.fillMaxSize(),
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = Spacing.xl, vertical = Spacing.xl),
            verticalArrangement = Arrangement.spacedBy(Spacing.lg)
        ) {
            HeroIcon(
                icon = Icons.Default.Star,
                modifier = Modifier.padding(top = Spacing.sm)
            )
            Text(
                text = if (trialAvailable && state != EntitlementState.PRO) {
                    "Try Pro before you subscribe"
                } else {
                    "Unlock full classification"
                },
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = "Pro adds scam warnings, risk scores, and clearer explanations for sensitive OTP codes. Free keeps basic local sorting on this phone.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface
            )
            InfoCard {
                ProBenefitLine(
                    title = "Know why a code came",
                    body = "See if a code looks like login, payment, account change, delivery, or another action."
                )
                ProBenefitLine(
                    title = "Spot risky messages",
                    body = "Checks suspicious links, urgency, sender patterns, and requests for passwords or OTPs."
                )
                ProBenefitLine(
                    title = "Warnings on sensitive codes",
                    body = "Adds context when a code should stay private."
                )
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = when (state) {
                    EntitlementState.PRO -> "You already have Pro."
                    EntitlementState.TRIAL_ACTIVE -> "Trial active — about $trialDays day(s) left."
                    EntitlementState.TRIAL_EXPIRED -> "Your trial has ended."
                    EntitlementState.FREE -> if (trialAvailable) {
                        "You have not used your $trialLabel Pro trial yet."
                    } else {
                        "You already used your $trialLabel Pro trial."
                    }
                },
                style = MaterialTheme.typography.bodyMedium
            )
            Spacer(modifier = Modifier.height(16.dp))
            if (trialAvailable && state != EntitlementState.PRO) {
                PrimaryButton(
                    text = "Start $trialLabel free trial",
                    onClick = {
                        AppContainer.telemetry.logCtaTap("paywall", "start_trial")
                        scope.launch {
                            if (entitlementManager.startTrialIfAvailableRemote()) {
                                entitlementRefresh++
                                AppContainer.telemetry.logEvent(
                                    "trial_started_from_paywall",
                                    mapOf("trigger" to telemetryTrigger)
                                )
                                onPurchaseFinishedNavigateNext()
                            } else {
                                snackbarHostState.showSnackbar(
                                    "Trial could not start. Check your connection and try again."
                                )
                            }
                        }
                    },
                    modifier = Modifier.fillMaxWidth()
                )
                Text(
                    text = "No payment method required. The trial does not start the paid subscription automatically.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(modifier = Modifier.height(4.dp))
            }
            val buyAction = {
                AppContainer.telemetry.logCtaTap("paywall", "unlock_pro")
                AppContainer.billingRepository.launchBillingFlow(activity)
            }
            if (trialAvailable && state != EntitlementState.PRO) {
                SecondaryButton(
                    text = "Subscribe - $annualPriceLabel",
                    onClick = buyAction,
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !billingInFlight
                )
            } else {
                PrimaryButton(
                    text = "Subscribe - $annualPriceLabel",
                    onClick = buyAction,
                    modifier = Modifier.fillMaxWidth(),
                    enabled = state != EntitlementState.PRO && !billingInFlight
                )
            }
            if (!BuildConfig.DEBUG && productDetails == null) {
                Text(
                    text = "Price loads when the Play subscription \"${PlayBillingRepository.SKU_PRO_YEARLY}\" is active in Play Console.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.error
                )
            }
            Text(
                text = "Annual Google Play subscription. Renews yearly unless canceled in Play Store.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            if (trialAvailable && state != EntitlementState.PRO) {
                Text(
                    text = "You can try scam warnings first. Subscribe only if Pro is useful.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            SecondaryButton(
                text = "Restore Pro",
                onClick = {
                    AppContainer.telemetry.logCtaTap("paywall", "restore_purchase")
                    AppContainer.billingRepository.restorePurchases()
                },
                modifier = Modifier.fillMaxWidth()
            )
            if (BuildConfig.DEBUG) {
                FilledTonalButton(
                    onClick = {
                        AppContainer.entitlementManager.setProPurchased(true)
                        onPurchaseFinishedNavigateNext()
                    },
                    modifier = Modifier.fillMaxWidth()
                ) { Text("Debug: grant Pro") }
            }
        }
    }
}

@Composable
private fun ProBenefitLine(title: String, body: String) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(
            text = title,
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.SemiBold
        )
        Text(
            text = body,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}
