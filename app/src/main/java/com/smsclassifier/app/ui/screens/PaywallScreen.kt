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
    val priceLabel = productDetails?.oneTimePurchaseOfferDetails?.formattedPrice ?: "…"
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
    }

    LaunchedEffect(Unit) {
        AppContainer.billingRepository.purchaseSuccess.collect {
            onPurchaseFinishedNavigateNext()
        }
    }

    val state = remember(entitlementRefresh) { entitlementManager.currentState() }
    val trialDays = remember(entitlementRefresh) { entitlementManager.trialDaysRemaining() }
    val trialAvailable = remember(entitlementRefresh) { !entitlementManager.hasTrialStarted() }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("SMS Classifier Pro", fontWeight = FontWeight.SemiBold) },
                navigationIcon = {
                    IconButton(onClick = onClose) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
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
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = if (trialAvailable && state != EntitlementState.PRO) {
                    "Try Pro before you buy"
                } else {
                    "Unlock full classification"
                },
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = "Pro is where cloud OTP intent, do-not-share warnings, phishing detection, and risk scoring run. Free keeps basic local classification only.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            ProBenefitLine(
                title = "OTP intent",
                body = "Shows whether a code looks like login, payment, account change, delivery, or another action."
            )
            ProBenefitLine(
                title = "Phishing risk",
                body = "Checks links, urgency, sender patterns, and credential or OTP-sharing requests."
            )
            ProBenefitLine(
                title = "Risk score and warnings",
                body = "Adds context such as \"do not share\" when a message looks sensitive."
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = when (state) {
                    EntitlementState.PRO -> "You already have Pro."
                    EntitlementState.TRIAL_ACTIVE -> "Trial active — about $trialDays day(s) left."
                    EntitlementState.TRIAL_EXPIRED -> "Your trial has ended."
                    EntitlementState.FREE -> if (trialAvailable) {
                        "You have not used your 7-day Pro trial yet."
                    } else {
                        "You already used your 7-day Pro trial."
                    }
                },
                style = MaterialTheme.typography.bodyMedium
            )
            Spacer(modifier = Modifier.height(16.dp))
            if (trialAvailable && state != EntitlementState.PRO) {
                Button(
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
                ) {
                    Text("Start 7-day Pro trial")
                }
                Text(
                    text = "No payment method required. No auto-charge during the trial.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.height(4.dp))
            }
            Button(
                onClick = {
                    AppContainer.telemetry.logCtaTap("paywall", "unlock_pro")
                    AppContainer.billingRepository.launchBillingFlow(activity)
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = state != EntitlementState.PRO && !billingInFlight
            ) {
                Text("Unlock Pro — $priceLabel")
            }
            if (!BuildConfig.DEBUG && productDetails == null) {
                Text(
                    text = "Price loads when the Play product \"${PlayBillingRepository.SKU_PRO_LIFETIME}\" is active in Play Console.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            }
            Text(
                text = "One-time purchase. No subscription.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            if (trialAvailable && state != EntitlementState.PRO) {
                Text(
                    text = "If you start the trial, you can test cloud phishing risk first, and nothing auto-charges when the trial ends.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            TextButton(
                onClick = {
                    AppContainer.telemetry.logCtaTap("paywall", "restore_purchase")
                    AppContainer.billingRepository.restorePurchases()
                },
                modifier = Modifier.fillMaxWidth()
            ) { Text("Restore purchase") }
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
