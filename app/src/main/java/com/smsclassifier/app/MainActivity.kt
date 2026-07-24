package com.smsclassifier.app

import android.Manifest
import android.app.role.RoleManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Telephony
import androidx.activity.ComponentActivity
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.ui.platform.LocalContext
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PrivacyTip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.foundation.layout.Box
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.AppContainer
import kotlinx.coroutines.flow.first
import androidx.compose.ui.Modifier
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.rememberNavController
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.navArgument
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.SettingsRepository
import com.smsclassifier.app.remote.AppRemoteConfigClient
import com.smsclassifier.app.remote.RemoteSafetyState
import com.smsclassifier.app.ui.screens.ComposeScreen
import com.smsclassifier.app.ui.screens.DetailScreen
import com.smsclassifier.app.ui.screens.InboxEntitlementUi
import com.smsclassifier.app.ui.screens.InboxScreen
import com.smsclassifier.app.ui.screens.PaywallScreen
import com.smsclassifier.app.ui.screens.PhoneAuthScreen
import com.smsclassifier.app.BuildConfig
import com.smsclassifier.app.billing.PlayBillingRepository
import com.smsclassifier.app.ui.screens.LogsScreen
import com.smsclassifier.app.ui.screens.NotificationDebugScreen
import com.smsclassifier.app.ui.screens.AboutSubScreen
import com.smsclassifier.app.ui.screens.DiagnosticsSubScreen
import com.smsclassifier.app.ui.screens.ExportSubScreen
import com.smsclassifier.app.ui.screens.NotificationSettingsSubScreen
import com.smsclassifier.app.ui.screens.SettingsScreen
import com.smsclassifier.app.ui.screens.ConversationListScreen
import com.smsclassifier.app.ui.screens.ThreadScreen
import com.smsclassifier.app.ui.components.SatisfactionPromptHost
import com.smsclassifier.app.ui.screens.ConsentOnboardingScreen
import com.smsclassifier.app.ui.screens.FlaggedScreen
import com.smsclassifier.app.ui.screens.MainBottomBar
import com.smsclassifier.app.ui.screens.OtpInboxScreen
import com.smsclassifier.app.ui.theme.SMSClassifierTheme
import com.smsclassifier.app.ui.theme.Spacing
import com.smsclassifier.app.ui.viewmodel.DetailViewModel
import com.smsclassifier.app.ui.viewmodel.InboxViewModel
import com.smsclassifier.app.ui.viewmodel.LogsViewModel
import com.smsclassifier.app.ui.viewmodel.NotificationDebugViewModel
import com.smsclassifier.app.ui.viewmodel.SettingsViewModel
import com.smsclassifier.app.ui.viewmodel.ConversationListViewModel
import com.smsclassifier.app.ui.viewmodel.ThreadViewModel
import com.smsclassifier.app.ui.viewmodel.ComposeViewModel
import com.smsclassifier.app.ui.viewmodel.OtpInboxViewModel
import com.smsclassifier.app.util.NotificationHelper
import com.smsclassifier.app.util.CrashlyticsBootstrap
import com.smsclassifier.app.work.SmsImportWorker
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull

class MainActivity : ComponentActivity() {
    private lateinit var database: AppDatabase
    private val defaultSmsAppState = mutableStateOf(false)
    
    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        
        database = AppDatabase.getDatabase(this)
        handleIntent(intent)
        defaultSmsAppState.value = isDefaultSmsAppNow()

        // Ensure notification channel is created
        NotificationHelper.createNotificationChannel(this)

        setContent {
            var gateReady by remember { mutableStateOf(false) }
            var needsConsent by remember { mutableStateOf(false) }
            var remoteSafety by remember { mutableStateOf(RemoteSafetyState.allow()) }
            LaunchedEffect(Unit) {
                val seen = runCatching {
                    withTimeoutOrNull(CONSENT_GATE_TIMEOUT_MS) {
                        AppContainer.consentManager.onboardingConsentSeen.first()
                    }
                }.onFailure { throwable ->
                    com.smsclassifier.app.util.AppLog.w(
                        "MainActivity",
                        "Consent gate read failed: ${throwable.message}"
                    )
                }.getOrNull() ?: AppContainer.consentManager.onboardingSeenNow()
                needsConsent = !seen
                remoteSafety = AppRemoteConfigClient()
                    .fetch(SettingsRepository(this@MainActivity).installId)
                    .getOrElse { RemoteSafetyState.allow() }
                gateReady = true
            }
            SMSClassifierTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    if (!gateReady) {
                        Box(
                            modifier = Modifier
                                .fillMaxSize()
                                .background(MaterialTheme.colorScheme.background),
                            contentAlignment = Alignment.Center
                        ) {
                            Column(
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.spacedBy(Spacing.lg)
                            ) {
                                Surface(
                                    shape = androidx.compose.foundation.shape.CircleShape,
                                    color = MaterialTheme.colorScheme.primaryContainer,
                                    tonalElevation = 1.dp
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.PrivacyTip,
                                        contentDescription = null,
                                        tint = MaterialTheme.colorScheme.primary,
                                        modifier = Modifier
                                            .size(80.dp)
                                            .padding(20.dp)
                                    )
                                }
                                Text(
                                    text = "SMS Classifier",
                                    style = MaterialTheme.typography.headlineMedium,
                                    fontWeight = FontWeight.SemiBold
                                )
                                CircularProgressIndicator(modifier = Modifier.size(28.dp))
                                Spacer(modifier = Modifier.height(Spacing.xs))
                            }
                        }
                    } else if (remoteSafety.blocksApp) {
                        RemoteSafetyBlockScreen(remoteSafety)
                    } else {
                        Box(modifier = Modifier.fillMaxSize()) {
                            val navController = rememberNavController()
                            val backStackEntry by navController.currentBackStackEntryAsState()
                            val currentRoute = backStackEntry?.destination?.route
                            val isDefaultSmsApp by defaultSmsAppState

                            var entitlementRefresh by remember { mutableStateOf(0) }
                            var inboxResetRequest by remember { mutableIntStateOf(0) }
                            val productDetails by AppContainer.billingRepository.productDetails.collectAsState(initial = null)
                            val formattedPrice = PlayBillingRepository.formattedAnnualPrice(productDetails)?.let { "$it/year" }

                    LaunchedEffect(Unit) {
                        AppContainer.billingRepository.purchaseSuccess.collect {
                            entitlementRefresh++
                        }
                    }

                    LaunchedEffect(backStackEntry?.destination?.route) {
                        if (backStackEntry?.destination?.route == "inbox") {
                            entitlementRefresh++
                        }
                    }

                    LaunchedEffect(currentRoute) {
                        currentRoute?.let { AppContainer.telemetry.logScreenView(it) }
                    }

                    val refreshEntitlement: () -> Unit = { entitlementRefresh++ }

                    val inboxEntitlementUi = remember(entitlementRefresh, formattedPrice) {
                        val em = AppContainer.entitlementManager
                        InboxEntitlementUi(
                            showTrialWelcome = em.shouldShowTrialStartedBanner(),
                            onTrialWelcomeDismiss = {
                                em.acknowledgeTrialStartedBanner()
                                refreshEntitlement()
                            },
                            trialNudgeMilestone = em.trialNudgeMilestone(),
                            trialDaysRemaining = em.trialDaysRemaining(),
                            formattedPrice = formattedPrice,
                            onTrialNudgeShown = { milestone ->
                                em.markTrialNudgeShown(milestone)
                            },
                            onTrialNudgeBuy = { milestone ->
                                AppContainer.telemetry.logTrialNudgeCta(milestone.daysRemaining)
                                navController.navigate("paywall/trial_ending")
                            },
                            onTrialNudgeDismiss = { milestone ->
                                em.markTrialNudgeShown(milestone)
                                refreshEntitlement()
                            },
                            showUnlockPro = em.showInboxUnlockProCta(),
                            onUnlockPro = {
                                navController.navigate("paywall/trial_expired")
                            }
                        )
                    }

                    // Handle intent extras for navigation
                    val composePhone = intent?.getStringExtra("compose_phone")
                    val composeMessage = intent?.getStringExtra("compose_message")
                    val openThreadId = intent?.getLongExtra("threadId", -1L)
                    val shouldOpenThread = intent?.getBooleanExtra("openThread", false) == true
                    val openMessageId = intent?.getLongExtra("messageId", -1L)
                    val shouldOpenDetail = intent?.getBooleanExtra("openDetail", false) == true

                    LaunchedEffect(composePhone, composeMessage) {
                        if (composePhone != null || composeMessage != null) {
                            navController.navigate("compose")
                        }
                    }

                    LaunchedEffect(openThreadId, shouldOpenThread) {
                        if (shouldOpenThread && openThreadId != -1L) {
                            navController.navigate("thread/$openThreadId")
                        }
                    }

                    LaunchedEffect(openMessageId, shouldOpenDetail) {
                        if (shouldOpenDetail && openMessageId != -1L) {
                            navController.navigate("detail/$openMessageId")
                        }
                    }

                    Scaffold(
                        bottomBar = {
                            if (currentRoute != "consent_onboarding") {
                                MainBottomBar(
                                    navController = navController,
                                    onInboxReselected = { inboxResetRequest++ }
                                )
                            }
                        }
                    ) { innerPadding ->
                        NavHost(
                            navController = navController,
                            startDestination = if (needsConsent) "consent_onboarding" else "inbox",
                            modifier = Modifier.padding(innerPadding)
                        ) {
                        composable("consent_onboarding") {
                            ConsentOnboardingScreen(
                                isDefaultSmsApp = isDefaultSmsApp,
                                onContinueBasic = {
                                    needsConsent = false
                                    navController.navigate("inbox") {
                                        popUpTo("consent_onboarding") { inclusive = true }
                                    }
                                },
                                onStartProTrial = {
                                    AppContainer.entitlementManager.startTrialIfAvailableRemote()
                                },
                                onContinueToInbox = {
                                    needsConsent = false
                                    navController.navigate("inbox") {
                                        popUpTo("consent_onboarding") { inclusive = true }
                                    }
                                },
                                onSetDefaultSms = { startDefaultSmsAndPermissionFlow() }
                            )
                        }
                        // Conversation list (home screen)
                        composable("conversations") {
                            val viewModel: ConversationListViewModel = viewModel(
                                factory = ConversationListViewModelFactory(database, this@MainActivity)
                            )
                            ConversationListScreen(
                                viewModel = viewModel,
                                onConversationClick = { threadId ->
                                    AppContainer.telemetry.logCtaTap("conversations", "thread_open")
                                    navController.navigate("thread/$threadId")
                                },
                                onNewMessageClick = {
                                    AppContainer.telemetry.logCtaTap("conversations", "new_message")
                                    navController.navigate("compose")
                                },
                                onOpenSettings = { navController.navigate("settings") }
                            )
                        }
                        
                        // Thread/Conversation view
                        composable(
                            route = "thread/{threadId}",
                            arguments = listOf(
                                navArgument("threadId") {
                                    type = NavType.LongType
                                }
                            )
                        ) { backStackEntry ->
                            val threadId = backStackEntry.arguments?.getLong("threadId") ?: 0L
                            val viewModel: ThreadViewModel = viewModel(
                                factory = ThreadViewModelFactory(database)
                            )
                            ThreadScreen(
                                threadId = threadId,
                                viewModel = viewModel,
                                onBack = { navController.popBackStack() },
                                onMessageClick = { messageId ->
                                    AppContainer.telemetry.logMessageOpen("thread")
                                    navController.navigate("detail/$messageId")
                                }
                            )
                        }
                        
                        // Compose new message
                        composable("compose") {
                            val viewModel: ComposeViewModel = viewModel()
                            val initialPhone = remember { composePhone }
                            val initialMessage = remember { composeMessage }
                            
                            LaunchedEffect(initialPhone, initialMessage) {
                                initialPhone?.let { viewModel.setAddress(it) }
                                initialMessage?.let { viewModel.setMessage(it) }
                            }
                            
                            ComposeScreen(
                                viewModel = viewModel,
                                initialAddress = initialPhone,
                                onBack = { navController.popBackStack() },
                                onMessageSent = {
                                    navController.popBackStack()
                                }
                            )
                        }
                        
                        // Inbox screen (shows conversations/threads)
                        composable("inbox") {
                            val viewModel: InboxViewModel = viewModel(
                                factory = InboxViewModelFactory(database)
                            )
                            InboxScreen(
                                viewModel = viewModel,
                                onMessageClick = { id ->
                                    AppContainer.telemetry.logMessageOpen("inbox")
                                    navController.navigate("detail/$id")
                                },
                                onThreadClick = { threadId ->
                                    AppContainer.telemetry.logCtaTap("inbox", "thread_open")
                                    navController.navigate("thread/$threadId")
                                },
                                onNewMessageClick = {
                                    AppContainer.telemetry.logCtaTap("inbox", "new_message")
                                    navController.navigate("compose")
                                },
                                onSetDefaultSms = { startDefaultSmsAndPermissionFlow() },
                                resetToAllRequest = inboxResetRequest,
                                entitlementUi = inboxEntitlementUi
                            )
                        }

                        composable("otp") {
                            val otpVm: OtpInboxViewModel = viewModel(
                                factory = OtpInboxViewModelFactory(database)
                            )
                            OtpInboxScreen(
                                viewModel = otpVm,
                                onMessageClick = { id ->
                                    AppContainer.telemetry.logMessageOpen("otp")
                                    navController.navigate("detail/$id")
                                }
                            )
                        }

                        composable("flagged") {
                            val flaggedVm: InboxViewModel = viewModel(
                                factory = InboxViewModelFactory(database)
                            )
                            FlaggedScreen(
                                viewModel = flaggedVm,
                                onMessageClick = { id ->
                                    AppContainer.telemetry.logMessageOpen("flagged")
                                    navController.navigate("detail/$id")
                                }
                            )
                        }
                        
                        composable(
                            route = "detail/{messageId}",
                            arguments = listOf(
                                navArgument("messageId") {
                                    type = NavType.LongType
                                }
                            )
                        ) { backStackEntry ->
                            val messageId = backStackEntry.arguments?.getLong("messageId") ?: 0L
                            val viewModel: DetailViewModel = viewModel(
                                factory = DetailViewModelFactory(database, this@MainActivity)
                            )
                            DetailScreen(
                                messageId = messageId,
                                viewModel = viewModel,
                                onBack = { navController.popBackStack() },
                                onOpenPaywall = {
                                    navController.navigate("paywall/feature_locked")
                                }
                            )
                        }
                        
                        composable("settings") {
                            val activity = LocalContext.current as ComponentActivity
                            val viewModel: SettingsViewModel = viewModel(
                                viewModelStoreOwner = activity,
                                factory = SettingsViewModelFactory(activity, database)
                            )
                            SettingsScreen(
                                viewModel = viewModel,
                                onBack = { navController.popBackStack() },
                                onDefaultSmsChanged = { startDefaultSmsAndPermissionFlow() },
                                onNavigateToNotifications = {
                                    navController.navigate("settings_notifications")
                                },
                                onNavigateToExport = { navController.navigate("settings_export") },
                                onNavigateToLogs = { navController.navigate("logs") },
                                onNavigateToAbout = { navController.navigate("settings_about") },
                                onNavigateToPaywall = { navController.navigate("paywall/settings") },
                                onNavigateToConsent = {
                                    navController.navigate("consent_onboarding") {
                                        popUpTo(navController.graph.id) { inclusive = true }
                                    }
                                }
                            )
                        }

                        composable("settings_notifications") {
                            val activity = LocalContext.current as ComponentActivity
                            val viewModel: SettingsViewModel = viewModel(
                                viewModelStoreOwner = activity,
                                factory = SettingsViewModelFactory(activity, database)
                            )
                            NotificationSettingsSubScreen(
                                viewModel = viewModel,
                                onBack = { navController.popBackStack() }
                            )
                        }

                        composable("settings_export") {
                            val activity = LocalContext.current as ComponentActivity
                            val viewModel: SettingsViewModel = viewModel(
                                viewModelStoreOwner = activity,
                                factory = SettingsViewModelFactory(activity, database)
                            )
                            ExportSubScreen(
                                viewModel = viewModel,
                                onBack = { navController.popBackStack() }
                            )
                        }

                        composable("settings_diagnostics") {
                            val activity = LocalContext.current as ComponentActivity
                            val viewModel: SettingsViewModel = viewModel(
                                viewModelStoreOwner = activity,
                                factory = SettingsViewModelFactory(activity, database)
                            )
                            DiagnosticsSubScreen(
                                viewModel = viewModel,
                                onBack = { navController.popBackStack() },
                                onOpenNotificationDebug = {
                                    if (BuildConfig.DEBUG) {
                                        navController.navigate("notification_debug")
                                    }
                                }
                            )
                        }

                        composable("settings_about") {
                            AboutSubScreen(
                                onBack = { navController.popBackStack() },
                                onUnlockDiagnostics = { navController.navigate("settings_diagnostics") }
                            )
                        }

                        composable("logs") {
                            val viewModel: LogsViewModel = viewModel(
                                factory = LogsViewModelFactory(database, this@MainActivity)
                            )
                            LogsScreen(
                                viewModel = viewModel,
                                onNavigateToSettings = { navController.navigate("settings") },
                                onBack = { navController.popBackStack() }
                            )
                        }

                        composable("notification_debug") {
                            val vm: NotificationDebugViewModel = viewModel(
                                factory = NotificationDebugViewModelFactory(database)
                            )
                            NotificationDebugScreen(
                                viewModel = vm,
                                onBack = { navController.popBackStack() }
                            )
                        }

                        composable(
                            route = "paywall/{trigger}",
                            arguments = listOf(
                                navArgument("trigger") {
                                    type = NavType.StringType
                                    defaultValue = "settings"
                                }
                            )
                        ) { entry ->
                            val trigger = entry.arguments?.getString("trigger") ?: "settings"
                            PaywallScreen(
                                onClose = { navController.popBackStack() },
                                onPurchaseFinishedNavigateNext = {
                                    navController.navigate("phone_auth") {
                                        popUpTo("paywall/{trigger}") { inclusive = true }
                                    }
                                },
                                telemetryTrigger = trigger
                            )
                        }

                        composable("phone_auth") {
                            PhoneAuthScreen(
                                onBack = { navController.popBackStack() },
                                onDoneSkip = { navController.popBackStack() }
                            )
                        }
                        }
                    }
                    SatisfactionPromptHost(
                        consentCompleted = !needsConsent,
                        currentRoute = currentRoute
                    )
                    }
                    }
                }
            }
        }
        if (AppContainer.consentManager.onboardingSeenNow()) {
            startDefaultSmsAndPermissionFlow()
        }
    }

    override fun onResume() {
        super.onResume()
        val def = isDefaultSmsAppNow()
        defaultSmsAppState.value = def
        AppContainer.telemetry.onMainActivityResume(def)
        CrashlyticsBootstrap.refresh(this, def)
        maybeEnqueueSmsImport()
        lifecycleScope.launch {
            AppContainer.entitlementManager.refreshFromServer()
        }
        AppContainer.billingRepository.restorePurchases()
    }

    private fun isDefaultSmsAppNow(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val roleManager = getSystemService(RoleManager::class.java)
            roleManager?.isRoleHeld(RoleManager.ROLE_SMS) ?: false
        } else {
            Telephony.Sms.getDefaultSmsPackage(this) == packageName
        }
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        intent?.let { handleIntent(it) }
    }
    
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQUEST_DEFAULT_SMS) {
            val defaultGranted = isDefaultSmsAppNow()
            defaultSmsAppState.value = defaultGranted
            AppContainer.telemetry.logEvent(
                if (defaultGranted) "default_sms_prompt_granted" else "default_sms_prompt_denied"
            )
            if (defaultGranted) {
                window.decorView.post {
                    requestSmsPermissionsIfNeeded()
                }
            } else {
                com.smsclassifier.app.util.AppLog.w(
                    "MainActivity",
                    "Default SMS role not granted; delaying runtime permission prompts"
                )
            }
        }
    }
    
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        when (requestCode) {
            REQUEST_NOTIFICATION_PERMISSION -> {
                val granted = grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED
                AppContainer.telemetry.logNotificationPermission(granted)
                if (granted) {
                    // Permission granted - notification channel already created in onCreate
                    com.smsclassifier.app.util.AppLog.d("MainActivity", "Notification permission granted")
                } else {
                    com.smsclassifier.app.util.AppLog.w("MainActivity", "Notification permission denied")
                }
            }
            REQUEST_SMS_PERMISSIONS -> {
                val allGranted = grantResults.isNotEmpty() &&
                    grantResults.all { it == PackageManager.PERMISSION_GRANTED }
                if (allGranted) {
                    AppContainer.telemetry.logEvent("sms_permissions_granted")
                    com.smsclassifier.app.util.AppLog.d("MainActivity", "SMS permissions granted")
                    maybeEnqueueSmsImport()
                } else {
                    AppContainer.telemetry.logEvent("sms_permissions_denied")
                    com.smsclassifier.app.util.AppLog.w("MainActivity", "SMS permissions denied")
                    // Show rationale or link to settings
                }
                requestNotificationPermissionIfNeeded()
            }
        }
    }
    
    private fun handleIntent(intent: Intent?) {
        when (intent?.action) {
            Intent.ACTION_SENDTO -> {
                // Handle SENDTO intent (compose new message)
                val data = intent.data
                val phoneNumber = data?.schemeSpecificPart // Extract phone number from sms: or smsto: URI
                val messageBody = intent.getStringExtra(Intent.EXTRA_TEXT) ?: ""
                
                // Navigate to compose screen with pre-filled data
                // This will be handled in the NavHost composable
                intent.putExtra("compose_phone", phoneNumber)
                intent.putExtra("compose_message", messageBody)
            }
            Intent.ACTION_VIEW -> {
                // Handle VIEW intent (open specific conversation)
                val data = intent.data
                val threadId = intent.getLongExtra("threadId", -1L)
                if (threadId != -1L) {
                    intent.putExtra("openThread", true)
                }
            }
        }
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (!isDefaultSmsAppNow()) {
            com.smsclassifier.app.util.AppLog.w(
                "MainActivity",
                "Default SMS role not held; delaying notification permission prompt"
            )
            return
        }

        // POST_NOTIFICATIONS permission is required for Android 13+ (API 33+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            when {
                ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.POST_NOTIFICATIONS
                ) == PackageManager.PERMISSION_GRANTED -> {
                    // Permission already granted
                    com.smsclassifier.app.util.AppLog.d("MainActivity", "Notification permission already granted")
                }
                ActivityCompat.shouldShowRequestPermissionRationale(
                    this,
                    Manifest.permission.POST_NOTIFICATIONS
                ) -> {
                    // User previously denied, show rationale (optional)
                    // For now, just request again
                    requestNotificationPermission()
                }
                else -> {
                    // Request permission
                    requestNotificationPermission()
                }
            }
        } else {
            // Android 12 and below - permission not needed
            com.smsclassifier.app.util.AppLog.d("MainActivity", "Android version < 13, notification permission not required")
        }
    }
    
    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                REQUEST_NOTIFICATION_PERMISSION
            )
        }
    }
    
    private fun requestSmsPermissionsIfNeeded() {
        if (!isDefaultSmsAppNow()) {
            com.smsclassifier.app.util.AppLog.w(
                "MainActivity",
                "Default SMS role not held; delaying SMS permission prompt"
            )
            return
        }

        // Check if we already have SMS permissions
        val hasReadSms = ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.READ_SMS
        ) == PackageManager.PERMISSION_GRANTED
        
        val hasReceiveSms = ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.RECEIVE_SMS
        ) == PackageManager.PERMISSION_GRANTED
        
        if (hasReadSms && hasReceiveSms) {
            com.smsclassifier.app.util.AppLog.d("MainActivity", "SMS permissions already granted")
            maybeEnqueueSmsImport()
            requestNotificationPermissionIfNeeded()
            return
        }
        
        // Request permissions if not granted
        val permissionsToRequest = mutableListOf<String>()
        if (!hasReadSms) {
            permissionsToRequest.add(Manifest.permission.READ_SMS)
        }
        if (!hasReceiveSms) {
            permissionsToRequest.add(Manifest.permission.RECEIVE_SMS)
        }
        
        if (permissionsToRequest.isNotEmpty()) {
            // Check if we should show rationale
            val shouldShowRationale = permissionsToRequest.any { permission ->
                ActivityCompat.shouldShowRequestPermissionRationale(this, permission)
            }
            AppContainer.telemetry.logEvent("sms_permissions_requested")
            
            if (shouldShowRationale) {
                // Show rationale dialog or snackbar explaining why permissions are needed
                // For now, just request directly
                ActivityCompat.requestPermissions(
                    this,
                    permissionsToRequest.toTypedArray(),
                    REQUEST_SMS_PERMISSIONS
                )
            } else {
                // Request permissions directly
                ActivityCompat.requestPermissions(
                    this,
                    permissionsToRequest.toTypedArray(),
                    REQUEST_SMS_PERMISSIONS
                )
            }
        }
    }

    private fun startDefaultSmsAndPermissionFlow() {
        if (isDefaultSmsAppNow()) {
            requestSmsPermissionsIfNeeded()
            return
        }

        if (!launchDefaultSmsPrompt()) {
            com.smsclassifier.app.util.AppLog.w(
                "MainActivity",
                "Default SMS prompt unavailable; runtime permission prompts delayed"
            )
        }
    }

    private fun launchDefaultSmsPrompt(): Boolean {
        val intent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val roleManager = getSystemService(RoleManager::class.java)
            if (roleManager?.isRoleAvailable(RoleManager.ROLE_SMS) == true) {
                roleManager.createRequestRoleIntent(RoleManager.ROLE_SMS)
            } else {
                AppContainer.telemetry.logEvent("default_sms_prompt_unavailable")
                return false
            }
        } else {
            Intent(Telephony.Sms.Intents.ACTION_CHANGE_DEFAULT).apply {
                putExtra(Telephony.Sms.Intents.EXTRA_PACKAGE_NAME, packageName)
            }
        }

        return runCatching {
            AppContainer.telemetry.logEvent("default_sms_prompt_shown")
            startActivityForResult(intent, REQUEST_DEFAULT_SMS)
            true
        }.getOrElse { throwable ->
            AppContainer.telemetry.logEvent("default_sms_prompt_unavailable")
            com.smsclassifier.app.util.AppLog.w(
                "MainActivity",
                "Unable to launch default SMS prompt: ${throwable.message}"
            )
            false
        }
    }

    private fun maybeEnqueueSmsImport() {
        SmsImportWorker.enqueue(this)
    }

    companion object {
        private const val REQUEST_DEFAULT_SMS = 1001
        private const val REQUEST_NOTIFICATION_PERMISSION = 1002
        private const val REQUEST_SMS_PERMISSIONS = 1003
        private const val CONSENT_GATE_TIMEOUT_MS = 2_000L
    }
}

@Composable
private fun RemoteSafetyBlockScreen(state: RemoteSafetyState) {
    val context = LocalContext.current
    val title = if (state.updateRequired) "Update SMS Classifier" else "SMS Classifier is paused"
    val message = state.message ?: if (state.updateRequired) {
        "Please update to the latest version to keep using SMS Classifier."
    } else {
        "SMS Classifier is temporarily unavailable. Please try again later."
    }
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(Spacing.xl),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Surface(
            shape = androidx.compose.foundation.shape.CircleShape,
            color = MaterialTheme.colorScheme.primaryContainer,
            tonalElevation = 1.dp
        ) {
            Icon(
                imageVector = Icons.Default.PrivacyTip,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier
                    .size(80.dp)
                    .padding(20.dp)
            )
        }
        Spacer(modifier = Modifier.height(Spacing.lg))
        Text(
            text = title,
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.SemiBold
        )
        Spacer(modifier = Modifier.height(Spacing.sm))
        Text(
            text = message,
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        if (state.updateRequired) {
            Spacer(modifier = Modifier.height(Spacing.lg))
            Button(
                onClick = {
                    val target = state.updateUrl
                        ?: "market://details?id=${BuildConfig.APPLICATION_ID}"
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(target))
                    runCatching { context.startActivity(intent) }.onFailure {
                        context.startActivity(
                            Intent(
                                Intent.ACTION_VIEW,
                                Uri.parse(
                                    "https://play.google.com/store/apps/details?id=${BuildConfig.APPLICATION_ID}"
                                )
                            )
                        )
                    }
                }
            ) {
                Text("Update")
            }
        }
    }
}

// ViewModel Factories
class InboxViewModelFactory(private val database: AppDatabase) :
    ViewModelProvider.Factory {
    override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(InboxViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return InboxViewModel(database) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}

class DetailViewModelFactory(
    private val database: AppDatabase,
    private val context: Context? = null
) : ViewModelProvider.Factory {
    override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(DetailViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return DetailViewModel(database, context) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}

class SettingsViewModelFactory(
    private val context: android.content.Context,
    private val database: AppDatabase
) : ViewModelProvider.Factory {
    override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(SettingsViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return SettingsViewModel(context, database) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}

class LogsViewModelFactory(
    private val database: AppDatabase,
    private val context: Context
) : ViewModelProvider.Factory {
    override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(LogsViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return LogsViewModel(database, context) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}

class NotificationDebugViewModelFactory(
    private val database: AppDatabase
) : ViewModelProvider.Factory {
    override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(NotificationDebugViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return NotificationDebugViewModel(database) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}

class ConversationListViewModelFactory(
    private val database: AppDatabase,
    private val context: Context
) : ViewModelProvider.Factory {
    override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(ConversationListViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return ConversationListViewModel(database, context) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}

class ThreadViewModelFactory(
    private val database: AppDatabase
) : ViewModelProvider.Factory {
    override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(ThreadViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return ThreadViewModel(database) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}

class OtpInboxViewModelFactory(
    private val database: AppDatabase
) : ViewModelProvider.Factory {
    override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(OtpInboxViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return OtpInboxViewModel(database) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}
