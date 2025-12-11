package com.smsclassifier.app

import android.Manifest
import android.app.role.RoleManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.provider.Telephony
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.ui.screens.DetailScreen
import com.smsclassifier.app.ui.screens.InboxScreen
import com.smsclassifier.app.ui.screens.LogsScreen
import com.smsclassifier.app.ui.screens.SettingsScreen
import com.smsclassifier.app.ui.screens.ConversationListScreen
import com.smsclassifier.app.ui.screens.ThreadScreen
import com.smsclassifier.app.ui.screens.ComposeScreen
import com.smsclassifier.app.ui.theme.SMSClassifierTheme
import com.smsclassifier.app.ui.viewmodel.DetailViewModel
import com.smsclassifier.app.ui.viewmodel.InboxViewModel
import com.smsclassifier.app.ui.viewmodel.LogsViewModel
import com.smsclassifier.app.ui.viewmodel.SettingsViewModel
import com.smsclassifier.app.ui.viewmodel.ConversationListViewModel
import com.smsclassifier.app.ui.viewmodel.ThreadViewModel
import com.smsclassifier.app.ui.viewmodel.ComposeViewModel
import com.smsclassifier.app.util.NotificationHelper

class MainActivity : ComponentActivity() {
    private lateinit var database: AppDatabase
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        database = AppDatabase.getDatabase(this)
        handleIntent(intent)
        
        // Request SMS permissions first (needed before default SMS handler)
        requestSmsPermissionsIfNeeded()
        
        // Request notification permission for Android 13+ (API 33+)
        requestNotificationPermissionIfNeeded()
        
        // Ensure notification channel is created
        NotificationHelper.createNotificationChannel(this)
        
        promptForDefaultSmsIfNeeded()
        
        setContent {
            SMSClassifierTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val navController = rememberNavController()
                    
                    // Handle intent extras for navigation
                    val composePhone = intent?.getStringExtra("compose_phone")
                    val composeMessage = intent?.getStringExtra("compose_message")
                    val openThreadId = intent?.getLongExtra("threadId", -1L)
                    val shouldOpenThread = intent?.getBooleanExtra("openThread", false) == true
                    
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
                    
                    NavHost(
                        navController = navController,
                        startDestination = "inbox"
                    ) {
                        // Conversation list (home screen)
                        composable("conversations") {
                            val viewModel: ConversationListViewModel = viewModel(
                                factory = ConversationListViewModelFactory(database, this@MainActivity)
                            )
                            ConversationListScreen(
                                viewModel = viewModel,
                                onConversationClick = { threadId ->
                                    navController.navigate("thread/$threadId")
                                },
                                onNewMessageClick = {
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
                                    navController.navigate("detail/$id")
                                },
                                onThreadClick = { threadId ->
                                    navController.navigate("thread/$threadId")
                                },
                                onNewMessageClick = {
                                    navController.navigate("compose")
                                },
                                onOpenLogs = { navController.navigate("logs") },
                                onOpenSettings = { navController.navigate("settings") }
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
                                onBack = { navController.popBackStack() }
                            )
                        }
                        
                        composable("settings") {
                            val viewModel: SettingsViewModel = viewModel(
                                factory = SettingsViewModelFactory(this@MainActivity, database)
                            )
                            SettingsScreen(
                                viewModel = viewModel,
                                onBack = { navController.popBackStack() }
                            )
                        }

                        composable("logs") {
                            val viewModel: LogsViewModel = viewModel(
                                factory = LogsViewModelFactory(database)
                            )
                            LogsScreen(
                                viewModel = viewModel,
                                onBack = { navController.popBackStack() }
                            )
                        }
                    }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        intent?.let { handleIntent(it) }
    }
    
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQUEST_DEFAULT_SMS) {
            // no-op; Settings screen observes state and will refresh
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
                if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                    // Permission granted - notification channel already created in onCreate
                    com.smsclassifier.app.util.AppLog.d("MainActivity", "Notification permission granted")
                } else {
                    // Permission denied - user won't receive notifications
                    com.smsclassifier.app.util.AppLog.w("MainActivity", "Notification permission denied")
                }
            }
            REQUEST_SMS_PERMISSIONS -> {
                val allGranted = grantResults.all { it == PackageManager.PERMISSION_GRANTED }
                if (allGranted) {
                    com.smsclassifier.app.util.AppLog.d("MainActivity", "SMS permissions granted")
                } else {
                    com.smsclassifier.app.util.AppLog.w("MainActivity", "SMS permissions denied")
                    // Show rationale or link to settings
                }
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
    
    private fun promptForDefaultSmsIfNeeded() {
        // Check if already default SMS handler
        val isDefault = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val roleManager = getSystemService(RoleManager::class.java)
            roleManager?.isRoleHeld(RoleManager.ROLE_SMS) ?: false
        } else {
            Telephony.Sms.getDefaultSmsPackage(this) == packageName
        }
        
        if (!isDefault) {
            // Show prompt after a short delay to let UI load
            window.decorView.postDelayed({
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    val roleManager = getSystemService(RoleManager::class.java)
                    if (roleManager?.isRoleAvailable(RoleManager.ROLE_SMS) == true) {
                        val intent = roleManager.createRequestRoleIntent(RoleManager.ROLE_SMS)
                        startActivityForResult(intent, REQUEST_DEFAULT_SMS)
                    }
                } else {
                    val intent = Intent(Telephony.Sms.Intents.ACTION_CHANGE_DEFAULT).apply {
                        putExtra(Telephony.Sms.Intents.EXTRA_PACKAGE_NAME, packageName)
                    }
                    startActivityForResult(intent, REQUEST_DEFAULT_SMS)
                }
            }, 1000) // 1 second delay
        }
    }

    companion object {
        private const val REQUEST_DEFAULT_SMS = 1001
        private const val REQUEST_NOTIFICATION_PERMISSION = 1002
        private const val REQUEST_SMS_PERMISSIONS = 1003
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
    private val database: AppDatabase
) : ViewModelProvider.Factory {
    override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(LogsViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return LogsViewModel(database) as T
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

