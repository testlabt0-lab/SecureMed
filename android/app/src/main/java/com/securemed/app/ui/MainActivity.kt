package com.securemed.app.ui

import android.Manifest
import android.content.Intent
import android.os.Build
import android.os.Bundle
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
import com.securemed.app.BuildConfig
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.reminders.NotificationHelper
import com.securemed.app.navigation.Route
import com.securemed.app.security.AppLock
import com.securemed.app.security.SecurityUtils
import com.securemed.app.ui.components.BottomNavBar
import com.securemed.app.ui.screens.*
import com.securemed.app.ui.theme.SecureMedTheme
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.delay

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

    // ===== Idle lock =====
    //
    // The activity's only job here is to report interaction and to ask
    // [AppLock] to judge the idle time; the rule itself, and the reasons the
    // previous Handler-based timeout could not enforce it, live in that class.

    override fun dispatchTouchEvent(ev: MotionEvent?): Boolean {
        AppLock.noteInteraction()
        return super.dispatchTouchEvent(ev)
    }

    /** Hardware keys and D-pad input, which never reach dispatchTouchEvent. */
    override fun onUserInteraction() {
        super.onUserInteraction()
        AppLock.noteInteraction()
    }

    override fun onResume() {
        super.onResume()
        // Judge before marking: the mark left behind when the app last lost
        // focus is the only evidence of how long it has been untouched, and
        // noting an interaction first would erase it.
        if (!AppLock.lockIfIdle()) {
            AppLock.noteInteraction(force = true)
        }
    }

    override fun onPause() {
        super.onPause()
        // The last moment the app can observe the user, so the throttle is
        // bypassed: an interaction from a second ago must not be recorded as
        // fifteen seconds ago once the session is judged on the next resume.
        AppLock.noteInteraction(force = true)
    }
    // =========================================

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        
        // فحص الروت — في نسخ الإصدار فقط.
        //
        // كان الفحص يشمل كشف المحاكي أيضاً، فكان التطبيق يُغلق نفسه على كل
        // محاكي؛ وحتى بعد فصلهما تبقى صور المحاكي موقّعة بـ test-keys، لذا
        // يُستثنى بناء التطوير كي يظل التطبيق قابلاً للتشغيل والاختبار.
        if (!BuildConfig.DEBUG && SecurityUtils.isDeviceRooted()) {
            android.widget.Toast.makeText(this, "عذراً، لا يمكن تشغيل هذا التطبيق على أجهزة مكسورة الحماية (Rooted) لأسباب أمنية.", android.widget.Toast.LENGTH_LONG).show()
            finishAffinity()
            return
        }

        // Runtime instrumentation check (Frida / Xposed / attached debugger).
        // Release-only, same reasoning as the root check: a debug build that
        // refused to run under a debugger would stop every developer at once.
        // The response to tampering is to wipe every local trace of the
        // session before closing — a hooked process must not be left holding
        // PHI, tokens, or a device identity the attacker can reuse.
        if (!BuildConfig.DEBUG && com.securemed.app.security.TamperDetection
                .isTamperingDetected(this)) {
            com.securemed.app.security.SecureWipe.wipeEverything(this)
            android.widget.Toast.makeText(this, "رُصدت أدوات تحليل على هذا الجهاز. تم مسح البيانات المحلية وإغلاق التطبيق.", android.widget.Toast.LENGTH_LONG).show()
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
                            else -> Route.DeviceCheck.route
                        }
                    }

                    // The single way out of a session: the logout buttons on the
                    // dashboard and the profile, the all-devices row in settings,
                    // and the lock screen — where it is the only way forward for a
                    // device that cannot satisfy an unlock prompt at all.
                    //
                    // [allDevices] decides whether the server ends only this
                    // session or every session the account holds; the lock is
                    // lifted synchronously inside AuthViewModel.logout, before the
                    // network call, so the overlay never outlives the session it
                    // was covering.
                    //
                    // popUpTo(0) clears the whole back stack. The per-screen
                    // versions this replaced popped up to the dashboard, which a
                    // session started by tapping a dose reminder never visited —
                    // leaving the medications list, patient name included, one
                    // back press behind the login screen.
                    val signOut: (Boolean) -> Unit = { allDevices ->
                        authViewModel.logout(allDevices)
                        navController.navigate(Route.DeviceCheck.route) {
                            popUpTo(0) { inclusive = true }
                        }
                    }

                    val locked by AppLock.locked.collectAsState()

                    // Someone reading a chart without touching the screen never
                    // produces an onPause, so the resume check alone would never
                    // fire for them. Coarse on purpose: the interaction mark is
                    // itself only written every 15 seconds, so a finer tick would
                    // buy nothing but wake-ups.
                    LaunchedEffect(Unit) {
                        while (true) {
                            delay(15_000L)
                            AppLock.lockIfIdle()
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
                            composable(Route.DeviceCheck.route) {
                                DeviceCheckScreen(
                                    viewModel = authViewModel,
                                    onDeviceAuthorized = {
                                        navController.navigate(Route.Login.route) {
                                            popUpTo(Route.DeviceCheck.route) { inclusive = true }
                                        }
                                    }
                                )
                            }
                            composable(Route.Login.route) {
                                LoginScreen(
                                    viewModel = authViewModel,
                                    onLoginSuccess = {
                                        // Starts the idle clock. Without it the
                                        // new session has no interaction mark at
                                        // all, and AppLock reads a missing mark as
                                        // "idle for an unknown time" — locking the
                                        // app in the first seconds after a login.
                                        AppLock.unlock()
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
                                    onNavigateToLabResults = { navController.navigate(Route.LabResults.route) },
                                    onNavigateToWards = { navController.navigate(Route.Wards.route) },
                                    onNavigateToInvoices = { navController.navigate(Route.Invoices.route) },
                                    onNavigateToAudit = { navController.navigate(Route.Audit.route) },
                                    onNavigateToReports = { navController.navigate(Route.Reports.route) },
                                    onLogout = { signOut(false) }
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
                                    onBack = { navController.popBackStack() },
                                    onOpenChat = {
                                        navController.navigate(
                                            Route.ChannelChat.createRoute(id)
                                        )
                                    }
                                )
                            }
                            composable(Route.ChannelChat.route) { backStackEntry ->
                                val id = backStackEntry.arguments?.getString("id") ?: ""
                                ChannelChatScreen(
                                    channelId = id,
                                    channelName = backStackEntry.arguments?.getString("name") ?: "",
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
                                    onLogout = { signOut(false) },
                                    onBack = { navController.popBackStack() },
                                    onNavigateToSettings = { navController.navigate(Route.Settings.route) }
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
                            composable(Route.LabResults.route) {
                                LabResultsScreen(onBack = { navController.popBackStack() })
                            }
                            composable(Route.Wards.route) {
                                WardsScreen(onBack = { navController.popBackStack() })
                            }
                            composable(Route.Invoices.route) {
                                InvoicesScreen(onBack = { navController.popBackStack() })
                            }
                            composable(Route.Audit.route) {
                                AuditScreen(onBack = { navController.popBackStack() })
                            }
                            composable(Route.Reports.route) {
                                ReportsScreen(onBack = { navController.popBackStack() })
                            }
                            composable(Route.Analytics.route) {
                                AnalyticsScreen(onBack = { navController.popBackStack() })
                            }
                            composable(Route.Settings.route) {
                                SettingsScreen(
                                    onBack = { navController.popBackStack() },
                                    // Biometric enrollment lives in the profile
                                    // screen, which is also where Settings was
                                    // opened from — pop back to it instead of
                                    // stacking a second copy.
                                    onNavigateToProfile = {
                                        navController.navigate(Route.Profile.route) {
                                            popUpTo(Route.Profile.route) { inclusive = true }
                                        }
                                    },
                                    onLogoutAllDevices = { signOut(true) },
                                    onAccountDeleted = {
                                        // The server deactivated the account and
                                        // ended every session; the ViewModel's
                                        // repository call already wiped the local
                                        // side (alarms, Room, tokens, cache). All
                                        // that remains here is the route to login.
                                        authViewModel.liftAppLockForSignedOut()
                                        navController.navigate(Route.DeviceCheck.route) {
                                            popUpTo(0) { inclusive = true }
                                        }
                                    }
                                )
                            }
                        }
                    }

                    // Drawn after the Scaffold and therefore over it, bottom bar
                    // included. A sibling of the navigation host rather than a
                    // destination inside it: Surface lays its children out like a
                    // Box, so every screen below stays composed and an unlock
                    // returns the user to the chart — and the half-typed note —
                    // they left.
                    if (locked) {
                        LockScreen(
                            onUnlocked = { AppLock.unlock() },
                            onSignOut = { signOut(false) }
                        )
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
