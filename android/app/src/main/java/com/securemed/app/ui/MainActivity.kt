package com.securemed.app.ui

import android.Manifest
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.fragment.app.FragmentActivity
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.reminders.NotificationHelper
import com.securemed.app.navigation.Route
import com.securemed.app.security.SecurityUtils
import com.securemed.app.ui.components.BottomNavBar
import com.securemed.app.ui.screens.*
import com.securemed.app.ui.theme.SecureMedTheme
import dagger.hilt.android.AndroidEntryPoint

/**
 * FragmentActivity (not plain ComponentActivity) because AndroidX
 * BiometricPrompt requires it — with a ComponentActivity the fingerprint
 * prompt silently never shows.
 */
@AndroidEntryPoint
class MainActivity : FragmentActivity() {

    private val notificationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            android.util.Log.d("SecureMed", "POST_NOTIFICATIONS granted=$granted")
        }

    // ===== Session Timeout (Inactivity) =====
    private val INACTIVITY_TIMEOUT_MS = 5 * 60 * 1000L // 5 دقائق
    private val timeoutHandler = Handler(Looper.getMainLooper())
    private var logoutAction: (() -> Unit)? = null

    private val logoutRunnable = Runnable {
        if (SecurePreferences.isLoggedIn()) {
            android.util.Log.w("SecureMed", "Session timed out due to inactivity.")
            logoutAction?.invoke()
        }
    }

    override fun dispatchTouchEvent(ev: MotionEvent?): Boolean {
        resetInactivityTimer()
        return super.dispatchTouchEvent(ev)
    }

    private fun resetInactivityTimer() {
        timeoutHandler.removeCallbacks(logoutRunnable)
        if (SecurePreferences.isLoggedIn()) {
            timeoutHandler.postDelayed(logoutRunnable, INACTIVITY_TIMEOUT_MS)
        }
    }

    override fun onResume() {
        super.onResume()
        resetInactivityTimer()
    }

    override fun onPause() {
        super.onPause()
        timeoutHandler.removeCallbacks(logoutRunnable)
    }
    // =========================================

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        
        // فحص الروت (Root Detection)
        if (SecurityUtils.isDeviceRooted()) {
            android.widget.Toast.makeText(this, "عذراً، لا يمكن تشغيل هذا التطبيق على أجهزة مكسورة الحماية (Rooted) لأسباب أمنية.", android.widget.Toast.LENGTH_LONG).show()
            finishAffinity()
            return
        }

        // منع أخذ لقطات الشاشة أو تسجيلها لحماية البيانات الطبية (Screenshot Protection)
        window.setFlags(
            WindowManager.LayoutParams.FLAG_SECURE,
            WindowManager.LayoutParams.FLAG_SECURE
        )

        enableEdgeToEdge()
        requestNotificationPermissionIfNeeded()

        // Tapping a medication reminder deep-links straight to the doses list.
        val openMedications =
            (intent?.getBooleanExtra(NotificationHelper.EXTRA_OPEN_MEDICATIONS, false) == true)

        setContent {
            SecureMedTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val navController = rememberNavController()
                    val authViewModel: AuthViewModel = hiltViewModel()

                    val startDestination = remember {
                        when {
                            SecurePreferences.isLoggedIn() && openMedications -> Route.Medications.route
                            SecurePreferences.isLoggedIn() -> Route.Dashboard.route
                            else -> Route.Login.route
                        }
                    }

                    // Register global logout action for Session Timeout
                    LaunchedEffect(Unit) {
                        logoutAction = {
                            authViewModel.logout()
                            navController.navigate(Route.Login.route) {
                                popUpTo(0) { inclusive = true }
                            }
                        }
                    }

                    val snackbarHostState = remember { androidx.compose.material3.SnackbarHostState() }
                    
                    LaunchedEffect(Unit) {
                        com.securemed.app.util.GlobalErrorHandler.errorFlow.collect { message ->
                            snackbarHostState.showSnackbar(
                                message = message,
                                duration = androidx.compose.material3.SnackbarDuration.Long
                            )
                        }
                    }

                    Scaffold(
                        snackbarHost = { androidx.compose.material3.SnackbarHost(snackbarHostState) },
                        bottomBar = { BottomNavBar(navController) }
                    ) { innerPadding ->
                        NavHost(
                            navController = navController,
                            startDestination = startDestination,
                            modifier = Modifier.padding(innerPadding),
                            enterTransition = { slideInHorizontally(initialOffsetX = { 1000 }) + fadeIn() },
                            exitTransition = { slideOutHorizontally(targetOffsetX = { -1000 }) + fadeOut() },
                            popEnterTransition = { slideInHorizontally(initialOffsetX = { -1000 }) + fadeIn() },
                            popExitTransition = { slideOutHorizontally(targetOffsetX = { 1000 }) + fadeOut() }
                        ) {
                            composable(Route.Login.route) {
                                LoginScreen(
                                    viewModel = authViewModel,
                                    onLoginSuccess = {
                                        navController.navigate(Route.Dashboard.route) {
                                            popUpTo(Route.Login.route) { inclusive = true }
                                        }
                                    }
                                )
                            }
                            composable(Route.Dashboard.route) {
                                DashboardScreen(
                                    onNavigateToChannels = { navController.navigate(Route.Channels.route) },
                                    onNavigateToPatients = { navController.navigate(Route.Patients.route) },
                                    onNavigateToMedications = { navController.navigate(Route.Medications.route) },
                                    onNavigateToUsers = { navController.navigate(Route.Users.route) },
                                    onNavigateToProfile = { navController.navigate(Route.Profile.route) },
                                    onNavigateToNotifications = { navController.navigate(Route.Notifications.route) },
                                    onNavigateToAppointments = { navController.navigate(Route.Appointments.route) },
                                    onNavigateToPharmacy = { navController.navigate(Route.Pharmacy.route) },
                                    onNavigateToLab = { navController.navigate(Route.Lab.route) },
                                    onNavigateToTelemedicine = { navController.navigate(Route.Telemedicine.route) },
                                    onNavigateToAnalytics = { navController.navigate(Route.Analytics.route) },
                                    onLogout = {
                                        authViewModel.logout()
                                        navController.navigate(Route.Login.route) {
                                            popUpTo(Route.Dashboard.route) { inclusive = true }
                                        }
                                    }
                                )
                            }
                            composable(Route.Notifications.route) {
                                NotificationsScreen(
                                    onBack = { navController.popBackStack() }
                                )
                            }
                            composable(Route.Channels.route) {
                                ChannelsScreen(
                                    onChannelClick = { id -> navController.navigate(Route.ChannelDetail.createRoute(id)) },
                                    onBack = { navController.popBackStack() }
                                )
                            }
                            composable(Route.ChannelDetail.route) { backStackEntry ->
                                val id = backStackEntry.arguments?.getString("id") ?: ""
                                ChannelDetailScreen(
                                    channelId = id,
                                    onBack = { navController.popBackStack() }
                                )
                            }
                            composable(Route.Patients.route) {
                                PatientsScreen(
                                    onPatientClick = { id -> navController.navigate(Route.PatientDetail.createRoute(id)) },
                                    onBack = { navController.popBackStack() }
                                )
                            }
                            composable(Route.Medications.route) {
                                MedicationsScreen(
                                    onBack = { navController.popBackStack() }
                                )
                            }
                            composable(Route.Users.route) {
                                UsersScreen(
                                    onBack = { navController.popBackStack() }
                                )
                            }
                            composable(Route.Profile.route) {
                                ProfileScreen(
                                    onLogout = {
                                        authViewModel.logout()
                                        navController.navigate(Route.Login.route) {
                                            popUpTo(Route.Dashboard.route) { inclusive = true }
                                        }
                                    },
                                    onBack = { navController.popBackStack() }
                                )
                            }
                            composable(Route.Appointments.route) {
                                AppointmentsScreen(onBack = { navController.popBackStack() })
                            }
                            composable(Route.PatientDetail.route) { backStackEntry ->
                                val id = backStackEntry.arguments?.getString("id") ?: ""
                                PatientDetailScreen(patientId = id, onBack = { navController.popBackStack() })
                            }
                            composable(Route.Pharmacy.route) {
                                PharmacyScreen(onBack = { navController.popBackStack() })
                            }
                            composable(Route.Lab.route) {
                                LabDashboardScreen(onBack = { navController.popBackStack() })
                            }
                            composable(Route.Telemedicine.route) {
                                TelemedicineScreen(onBack = { navController.popBackStack() })
                            }
                            composable(Route.Analytics.route) {
                                AnalyticsScreen(onBack = { navController.popBackStack() })
                            }
                            composable(Route.Settings.route) {
                                SettingsScreen(onBack = { navController.popBackStack() })
                            }
                        }
                    }
                }
            }
        }
    }

    /** Medication reminders are core functionality — ask on Android 13+. */
    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
            android.content.pm.PackageManager.PERMISSION_GRANTED
        ) {
            notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }
}
