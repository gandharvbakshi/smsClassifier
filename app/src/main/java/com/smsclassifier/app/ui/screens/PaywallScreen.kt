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
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.BuildConfig
import com.smsclassifier.app.billing.PlayBillingRepository
import com.smsclassifier.app.entitlement.EntitlementState

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

    val state = entitlementManager.currentState()
    val trialDays = entitlementManager.trialDaysRemaining()
    val trialAvailable = !entitlementManager.hasTrialStarted()

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
                    "Choose your 7-day Pro trial or one-time purchase"
                } else {
                    "Unlock full classification"
                },
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = "• Cloud OTP classification & intent\n• Cloud phishing detection & risk score\n• Start the trial first, or buy Pro once through Play Billing",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
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
                        if (entitlementManager.startTrialIfAvailable()) {
                            AppContainer.telemetry.logEvent(
                                "trial_started_from_paywall",
                                mapOf("trigger" to telemetryTrigger)
                            )
                            onPurchaseFinishedNavigateNext()
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
                onClick = { AppContainer.billingRepository.launchBillingFlow(activity) },
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
