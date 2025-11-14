package com.smsclassifier.app

import android.app.role.RoleManager
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.provider.Telephony
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
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
import com.smsclassifier.app.ui.screens.SettingsScreen
import com.smsclassifier.app.ui.theme.SMSClassifierTheme
import com.smsclassifier.app.ui.viewmodel.DetailViewModel
import com.smsclassifier.app.ui.viewmodel.InboxViewModel
import com.smsclassifier.app.ui.viewmodel.SettingsViewModel

class MainActivity : ComponentActivity() {
    private lateinit var database: AppDatabase
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        database = AppDatabase.getDatabase(this)
        promptForDefaultSmsIfNeeded()
        
        setContent {
            SMSClassifierTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val navController = rememberNavController()
                    
                    NavHost(
                        navController = navController,
                        startDestination = "inbox"
                    ) {
                        composable("inbox") {
                            val viewModel: InboxViewModel = viewModel(
                                factory = InboxViewModelFactory(database)
                            )
                            InboxScreen(
                                viewModel = viewModel,
                                onMessageClick = { id ->
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
                                factory = DetailViewModelFactory(database)
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
                            SettingsScreen(viewModel = viewModel)
                        }
                    }
                }
            }
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQUEST_DEFAULT_SMS) {
            // no-op; Settings screen observes state and will refresh
        }
    }

    private fun promptForDefaultSmsIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val roleManager = getSystemService(RoleManager::class.java)
            if (roleManager?.isRoleAvailable(RoleManager.ROLE_SMS) == true && !roleManager.isRoleHeld(RoleManager.ROLE_SMS)) {
                val intent = roleManager.createRequestRoleIntent(RoleManager.ROLE_SMS)
                startActivityForResult(intent, REQUEST_DEFAULT_SMS)
            }
        } else {
            val current = Telephony.Sms.getDefaultSmsPackage(this)
            if (current != packageName) {
                val intent = Intent(Telephony.Sms.Intents.ACTION_CHANGE_DEFAULT).apply {
                    putExtra(Telephony.Sms.Intents.EXTRA_PACKAGE_NAME, packageName)
                }
                startActivityForResult(intent, REQUEST_DEFAULT_SMS)
            }
        }
    }

    companion object {
        private const val REQUEST_DEFAULT_SMS = 1001
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

class DetailViewModelFactory(private val database: AppDatabase) :
    ViewModelProvider.Factory {
    override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(DetailViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return DetailViewModel(database) as T
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
            val prefs = context.getSharedPreferences("sms_classifier_prefs", android.content.Context.MODE_PRIVATE)
            @Suppress("UNCHECKED_CAST")
            return SettingsViewModel(context, database, prefs) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}

