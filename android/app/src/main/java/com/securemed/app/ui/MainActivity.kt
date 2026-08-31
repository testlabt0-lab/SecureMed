package com.securemed.app.ui

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.securemed.app.data.ConnectivityObserver
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.reminders.ReminderScheduler
import com.securemed.app.ui.screens.*
import com.securemed.app.ui.theme.SecureMedTheme

/**
 * FragmentActivity is REQUIRED for AndroidX BiometricPrompt — the
 * fingerprint dialog only attaches to a FragmentActivity (this was the
 * root cause of "fingerprint login does nothing").
 */
class MainActivity : FragmentActivity() {

    private val notificationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        requestNotificationPermissionIfNeeded()
        setContent {
            SecureMedTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val navController = rememberNavController()
                    val authViewModel: AuthViewModel = viewModel()
                    val context = LocalContext.current
                    val connectivity = remember { ConnectivityObserver(context) }
                    val isOnline by connectivity.isOnline.collectAsState()

                    // Refresh medication reminder alarms on every app start
                    // (alarms are cleared by device reboot; BootReceiver also
                    // reschedules, this covers update/force-stop cases).
                    if (SecurePreferences.isLoggedIn()) {
                        remember {
                            ReminderScheduler(context).refreshFromCache()
                        }
                    }

                    Column(modifier = Modifier.fillMaxSize()) {
                        // Offline banner — shown globally when connectivity is lost
                        AnimatedVisibility(visible = !isOnline) {
                            OfflineBanner()
                        }

                        Box(modifier = Modifier.weight(1f)) {
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
                                onNavigateToUsers = { navController.navigate("users") },
                                onNavigateToMedications = { navController.navigate("medications") },
                                onLogout = {
                                    authViewModel.logout()
                                    navController.navigate("login") {
                                        popUpTo("dashboard") { inclusive = true }
                                    }
                                }
                            )
                        }
                        composable("users") {
                            UsersScreen(
                                onBack = { navController.popBackStack() }
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
                        composable("medications") {
                            MedicationsScreen(
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
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            val granted = ContextCompat.checkSelfPermission(
                this, Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED
            if (!granted) {
                notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }
}

/**
 * Slim amber banner displayed above the whole app whenever the device has
 * no validated internet connection.
 */
@Composable
private fun OfflineBanner() {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.errorContainer)
            .padding(horizontal = 16.dp, vertical = 8.dp)
    ) {
        Row {
            Icon(
                Icons.Default.CloudOff,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onErrorContainer
            )
            Text(
                text = "لا يوجد اتصال بالإنترنت — يتم عرض البيانات المخزنة مؤقتاً",
                modifier = Modifier
                    .padding(start = 8.dp)
                    .align(Alignment.CenterVertically),
                color = MaterialTheme.colorScheme.onErrorContainer,
                style = MaterialTheme.typography.bodySmall
            )
        }
    }
}
