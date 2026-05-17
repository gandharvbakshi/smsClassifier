package com.smsclassifier.app.ui.screens

import android.app.Activity
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
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
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.auth.PhoneAuthUiState
import com.smsclassifier.app.ui.components.AppScaffold
import com.smsclassifier.app.ui.components.HeroIcon
import com.smsclassifier.app.ui.components.InfoCard
import com.smsclassifier.app.ui.components.PrimaryButton
import com.smsclassifier.app.ui.components.SecondaryButton
import com.smsclassifier.app.ui.theme.Spacing
import com.smsclassifier.app.util.CrashlyticsBootstrap
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

private data class DialCountry(val label: String, val dialDigits: String)

private val TOP_COUNTRIES = listOf(
    DialCountry("United States +1", "1"),
    DialCountry("India +91", "91"),
    DialCountry("United Kingdom +44", "44"),
    DialCountry("Canada +1", "1"),
    DialCountry("Australia +61", "61"),
    DialCountry("Germany +49", "49"),
    DialCountry("France +33", "33"),
    DialCountry("Brazil +55", "55"),
    DialCountry("Japan +81", "81"),
    DialCountry("Mexico +52", "52"),
)

private fun nationalValid(dialDigits: String, national: String): Boolean {
    val d = national.filter { it.isDigit() }
    if (d.length < 8 || d.length > 12) return false
    if (dialDigits == "91" && d.length != 10) return false
    return d.matches(Regex("\\d+"))
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PhoneAuthScreen(
    onBack: () -> Unit,
    onDoneSkip: () -> Unit,
    modifier: Modifier = Modifier
) {
    val activity = LocalContext.current as Activity
    val repo = remember { AppContainer.phoneAuthRepository }
    val state by repo.state.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    var countryIndex by remember { mutableIntStateOf(0) }
    var nationalNumber by remember { mutableStateOf("") }
    var otp by remember { mutableStateOf("") }
    var countryMenuExpanded by remember { mutableStateOf(false) }
    var resendSeconds by remember { mutableIntStateOf(0) }

    LaunchedEffect(Unit) {
        AppContainer.telemetry.logEvent("phone_auth_started")
    }

    LaunchedEffect(state) {
        when (val s = state) {
            is PhoneAuthUiState.AwaitingCode -> {
                resendSeconds = 30
            }
            is PhoneAuthUiState.Error -> {
                val reason = classifyErrorReason(s.message)
                AppContainer.telemetry.logEvent(
                    "phone_auth_completed",
                    mapOf("success" to false.toString(), "reason" to reason)
                )
                snackbarHostState.showSnackbar(s.message)
                repo.clearError()
                otp = ""
            }
            else -> {}
        }
    }

    val successUid = (state as? PhoneAuthUiState.Success)?.uid
    LaunchedEffect(successUid) {
        if (successUid == null) return@LaunchedEffect
        CrashlyticsBootstrap.setUserId(successUid)
        AppContainer.telemetry.logEvent(
            "phone_auth_completed",
            mapOf("success" to true.toString())
        )
        onDoneSkip()
    }

    LaunchedEffect(resendSeconds) {
        if (resendSeconds > 0) {
            delay(1000)
            resendSeconds--
        }
    }

    AppScaffold(
        title = "Link phone",
        onBack = onBack,
        snackbarHostState = snackbarHostState,
        modifier = modifier.fillMaxSize(),
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = Spacing.xl, vertical = Spacing.xl),
            verticalArrangement = Arrangement.spacedBy(Spacing.lg)
        ) {
            HeroIcon(icon = Icons.Default.Phone)
            Text(
                text = "Optional account link",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = "Add your phone for account recovery and support. You can skip this and keep using the app.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface
            )

            InfoCard {
            when (state) {
                is PhoneAuthUiState.AwaitingCode -> {
                    OutlinedTextField(
                        value = otp,
                        onValueChange = { v ->
                            otp = v.filter { it.isDigit() }.take(6)
                        },
                        label = { Text("6-digit code") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        textStyle = MaterialTheme.typography.headlineMedium,
                        modifier = Modifier.fillMaxWidth()
                    )
                    PrimaryButton(
                        text = "Verify code",
                        onClick = {
                            scope.launch {
                                if (otp.length == 6) repo.verifySmsCode(otp)
                                else snackbarHostState.showSnackbar("Enter the 6-digit code.")
                            }
                        },
                        modifier = Modifier.fillMaxWidth()
                    )
                    SecondaryButton(
                        text = if (resendSeconds > 0) "Resend in ${resendSeconds}s" else "Resend code",
                        onClick = {
                            if (resendSeconds == 0) {
                                val dial = TOP_COUNTRIES[countryIndex].dialDigits
                                val e164 = "+$dial${nationalNumber.filter { it.isDigit() }}"
                                repo.resend(activity, e164)
                            }
                        },
                        enabled = resendSeconds == 0,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
                else -> {
                    Box(modifier = Modifier.fillMaxWidth()) {
                        TextButton(
                            onClick = { countryMenuExpanded = true },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Country: ${TOP_COUNTRIES[countryIndex].label}")
                        }
                        DropdownMenu(
                            expanded = countryMenuExpanded,
                            onDismissRequest = { countryMenuExpanded = false }
                        ) {
                            TOP_COUNTRIES.forEachIndexed { i, c ->
                                DropdownMenuItem(
                                    text = { Text(c.label) },
                                    onClick = {
                                        countryIndex = i
                                        countryMenuExpanded = false
                                    }
                                )
                            }
                        }
                    }
                    OutlinedTextField(
                        value = nationalNumber,
                        onValueChange = { v ->
                            nationalNumber = v.filter { c -> c.isDigit() || c == ' ' }.take(15)
                        },
                        label = { Text("Phone number (no country code)") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                        textStyle = MaterialTheme.typography.titleLarge,
                        modifier = Modifier.fillMaxWidth()
                    )
                    PrimaryButton(
                        text = "Send code",
                        onClick = {
                            val dial = TOP_COUNTRIES[countryIndex].dialDigits
                            val nat = nationalNumber.filter { it.isDigit() }
                            if (!nationalValid(dial, nat)) {
                                scope.launch {
                                    snackbarHostState.showSnackbar("Enter a valid phone number.")
                                }
                            } else {
                                val e164 = "+$dial$nat"
                                repo.sendCode(activity, e164)
                            }
                        },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }
            }
            Spacer(modifier = Modifier.height(Spacing.md))
            SecondaryButton(
                text = "Skip for now",
                onClick = {
                    AppContainer.telemetry.logEvent(
                        "phone_auth_completed",
                        mapOf("success" to false.toString(), "reason" to "skipped")
                    )
                    onDoneSkip()
                },
                modifier = Modifier.fillMaxWidth()
            )
        }
    }
}

private fun classifyErrorReason(message: String): String = when {
    message.contains("not valid", ignoreCase = true) -> "invalid_code"
    message.contains("quota", ignoreCase = true) -> "quota"
    message.contains("invalid", ignoreCase = true) -> "invalid_request"
    else -> "verification_failed"
}
