package com.smsclassifier.app.ui.screens

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Inbox
import androidx.compose.material.icons.filled.Pin
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.currentBackStackEntryAsState

private data class TopLevelDestination(
    val route: String,
    val label: String,
    val icon: ImageVector
)

private val TopLevelDestinations = listOf(
    TopLevelDestination("inbox", "Inbox", Icons.Default.Inbox),
    TopLevelDestination("otp", "OTPs", Icons.Default.Pin),
    TopLevelDestination("flagged", "Flagged", Icons.Default.Warning),
    TopLevelDestination("settings", "Settings", Icons.Default.Settings)
)

@Composable
fun MainBottomBar(navController: NavHostController) {
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route
    val showBar = TopLevelDestinations.any { it.route == currentRoute }
    if (!showBar) return

    NavigationBar {
        TopLevelDestinations.forEach { dest ->
            NavigationBarItem(
                selected = currentRoute == dest.route,
                onClick = {
                    if (currentRoute == dest.route) return@NavigationBarItem
                    navController.navigate(dest.route) {
                        popUpTo(navController.graph.findStartDestination().id) {
                            saveState = true
                        }
                        launchSingleTop = true
                        restoreState = true
                    }
                },
                icon = { Icon(dest.icon, contentDescription = dest.label) },
                label = { Text(dest.label) }
            )
        }
    }
}
