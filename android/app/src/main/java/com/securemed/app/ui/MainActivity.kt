package com.securemed.app.ui

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.ui.screens.*
import com.securemed.app.ui.theme.SecureMedTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            SecureMedTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val navController = rememberNavController()
                    val authViewModel: AuthViewModel = viewModel()

                    NavHost(
                        navController = navController,
                        startDestination = if (SecurePreferences.isLoggedIn()) "dashboard" else "login"
                    ) {
                        composable("login") {
                            LoginScreen(
                                viewModel = authViewModel,
                                onLoginSuccess = {
                                    navController.navigate("dashboard") {
                                        popUpTo("login") { inclusive = true }
                                    }
                                }
                            )
                        }
                        composable("dashboard") {
                            DashboardScreen(
                                onNavigateToChannels = { navController.navigate("channels") },
                                onNavigateToPatients = { navController.navigate("patients") },
                                onNavigateToProfile = { navController.navigate("profile") },
                                onNavigateToNotifications = { navController.navigate("notifications") },
                                onLogout = {
                                    authViewModel.logout()
                                    navController.navigate("login") {
                                        popUpTo("dashboard") { inclusive = true }
                                    }
                                }
                            )
                        }
                        composable("notifications") {
                            NotificationsScreen(
                                onBack = { navController.popBackStack() }
                            )
                        }
                        composable("channels") {
                            ChannelsScreen(
                                onChannelClick = { id -> navController.navigate("channel/$id") },
                                onBack = { navController.popBackStack() }
                            )
                        }
                        composable("channel/{id}") { backStackEntry ->
                            val id = backStackEntry.arguments?.getString("id") ?: ""
                            ChannelDetailScreen(
                                channelId = id,
                                onBack = { navController.popBackStack() }
                            )
                        }
                        composable("patients") {
                            PatientsScreen(
                                onBack = { navController.popBackStack() }
                            )
                        }
                        composable("profile") {
                            ProfileScreen(
                                onLogout = {
                                    authViewModel.logout()
                                    navController.navigate("login") {
                                        popUpTo("dashboard") { inclusive = true }
                                    }
                                },
                                onBack = { navController.popBackStack() }
                            )
                        }
                    }
                }
            }
        }
    }
}
