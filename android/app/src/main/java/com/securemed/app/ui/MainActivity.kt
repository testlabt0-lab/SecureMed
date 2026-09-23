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
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.securemed.app.BuildConfig
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.hardware.barcode.BarcodeScannerModal
import com.securemed.app.reminders.NotificationHelper
import com.securemed.app.navigation.Route
import com.securemed.app.security.AppLock
import com.securemed.app.security.SecurityUtils
import com.securemed.app.ui.components.BottomNavBar
import com.securemed.app.ui.screens.*
import com.securemed.app.ui.theme.SecureMedTheme
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * FragmentActivity (not plain ComponentActivity) because AndroidX
 * BiometricPrompt requires it — with a ComponentActivity the fingerprint
 * prompt silently never shows.
 */
@AndroidEntryPoint
class MainActivity : FragmentActivity() {

    @Inject
    lateinit var repository: com.securemed.app.data.SecureMedRepository

    private val pendingShortcutAction = MutableStateFlow<String?>(null)

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        intent.getStringExtra("extra_action")?.let { action ->
            pendingShortcutAction.value = action
        }
    }

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
        updateScreenshotProtection()
        // Judge before marking: the mark left behind when the app last lost
        // focus is the only evidence of how long it has been untouched, and
        // noting an interaction first would erase it.
        if (!AppLock.lockIfIdle()) {
            AppLock.noteInteraction(force = true)
        }
    }

    override fun onPause() {
        super.onPause()
        // مسح الحافظة فوراً عند خروج التطبيق للخلفية لمنع تسريب بيانات المرضى
        com.securemed.app.security.ClipboardSanitizer.clearClipboard(this)
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
        if (abortIfRooted()) return

        // Runtime instrumentation check (Frida / Xposed / attached debugger).
        if (abortIfTampered()) return

        // منع أخذ لقطات الشاشة أو تسجيلها لحماية البيانات الطبية (Screenshot Protection) ديناميكياً
        intent?.getStringExtra("extra_action")?.let { action ->
            pendingShortcutAction.value = action
        }

        updateScreenshotProtection()

        // منع هجمات النوافذ العائمة والتنصت على اللمس (Anti-Tapjacking Protection)
        window.decorView.filterTouchesWhenObscured = true

        // فحص مخاطر الشاشة وخدمات الوصول غير المصرح بها
        recordOverlayRisks()

        enableEdgeToEdge()
        requestNotificationPermissionIfNeeded()

        // Tapping a medication reminder deep-links straight to the doses list.
        val openMedications =
            (intent?.getBooleanExtra(NotificationHelper.EXTRA_OPEN_MEDICATIONS, false) == true)

        setContent {
            SecureMedTheme {
                SecureMedAppContent(
                    activity = this@MainActivity,
                    pendingShortcutAction = pendingShortcutAction,
                    openMedications = openMedications
                )
            }
        }
    }

    /**
     * Release-only root gate. Returns true (and blocks the launch with a
     * non-cancellable dialog) when the device is rooted, so onCreate aborts.
     */
    private fun abortIfRooted(): Boolean {
        if (BuildConfig.DEBUG || !SecurityUtils.isDeviceRooted()) return false
        android.app.AlertDialog.Builder(this)
            .setTitle("تنبيه أمني")
            .setMessage("عذراً، لا يمكن تشغيل هذا التطبيق على أجهزة مكسورة الحماية (Rooted) لأسباب أمنية.")
            .setCancelable(false)
            .setPositiveButton("إغلاق") { _, _ -> finishAffinity() }
            .show()
        return true
    }

    /**
     * Release-only runtime-instrumentation gate (Frida / Xposed / attached
     * debugger). Wipes local data and unregisters the FCM token before
     * blocking the launch, so a hooked environment never holds patient data.
     */
    private fun abortIfTampered(): Boolean {
        if (BuildConfig.DEBUG ||
            !com.securemed.app.security.TamperDetection.isTamperingDetected(this)
        ) return false
        kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.IO).launch {
            runCatching { repository.unregisterCurrentFcmToken() }
        }
        com.securemed.app.security.SecureWipe.wipeEverything(this)
        android.app.AlertDialog.Builder(this)
            .setTitle("تحذير أمني")
            .setMessage("رُصدت أدوات تحليل أو تلاعب على هذا الجهاز. تم مسح البيانات المحلية لحماية السجلات الطبية.")
            .setCancelable(false)
            .setPositiveButton("إغلاق") { _, _ -> finishAffinity() }
            .show()
        return true
    }

    /** Records every active overlay/accessibility risk into the audit chain. */
    private fun recordOverlayRisks() {
        val overlayRisks = com.securemed.app.security.OverlayDetector.scanForRisks(this)
        for (risk in overlayRisks) {
            com.securemed.app.security.TamperProofAuditManager.recordEvent(
                this,
                "OVERLAY_RISK_DETECTED",
                risk.description
            )
        }
    }

    private fun updateScreenshotProtection() {
        if (SecurePreferences.isScreenshotProtectionEnabled) {
            window.setFlags(
                WindowManager.LayoutParams.FLAG_SECURE,
                WindowManager.LayoutParams.FLAG_SECURE
            )
        } else {
            window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
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

/**
 * Root composable: holds the nav controller, the session-wide side effects
 * (idle lock, screen-mirroring poll, global error snackbars), the navigation
 * host, and the overlays drawn above it (lock screen, mirroring block, global
 * barcode scanner).
 */
@Composable
private fun SecureMedAppContent(
    activity: MainActivity,
    pendingShortcutAction: MutableStateFlow<String?>,
    openMedications: Boolean
) {
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        val navController = rememberNavController()
        val authViewModel: AuthViewModel = hiltViewModel()

        val shortcutAction by pendingShortcutAction.collectAsState()
        var showGlobalBarcodeScanner by remember { mutableStateOf(false) }

        LaunchedEffect(shortcutAction) {
            handleShortcutAction(
                action = shortcutAction,
                activity = activity,
                navController = navController,
                pendingShortcutAction = pendingShortcutAction,
                onShowScanner = { showGlobalBarcodeScanner = true }
            )
        }

        val startDestination = remember {
            when {
                SecurePreferences.isLoggedIn() && openMedications -> Route.Medications.route
                SecurePreferences.isLoggedIn() -> Route.Dashboard.route
                SecurePreferences.isDeviceAuthorized -> Route.Login.route
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
            val target = if (SecurePreferences.isDeviceAuthorized) Route.Login.route else Route.DeviceCheck.route
            navController.navigate(target) {
                popUpTo(0) { inclusive = true }
            }
        }

        val locked by AppLock.locked.collectAsState()

        var isScreenMirrored by remember {
            mutableStateOf(SecurityUtils.isScreenMirrored(activity))
        }
        // Event-driven instead of a fixed 5-second poll: the listener fires the
        // instant an external display is added, changed, or removed (casting
        // starting or stopping), so the PHI block appears without a poll delay
        // and costs nothing at idle. The resume hook re-checks after the user
        // may have flipped the protection toggle in Settings — that preference
        // is read synchronously and emits no event of its own.
        DisposableEffect(Unit) {
            val displayManager = activity.getSystemService(android.content.Context.DISPLAY_SERVICE)
                as? android.hardware.display.DisplayManager
            val recheck = { isScreenMirrored = SecurityUtils.isScreenMirrored(activity) }
            val listener = object : android.hardware.display.DisplayManager.DisplayListener {
                override fun onDisplayAdded(displayId: Int) = recheck()
                override fun onDisplayChanged(displayId: Int) = recheck()
                override fun onDisplayRemoved(displayId: Int) = recheck()
            }
            displayManager?.registerDisplayListener(listener, null)
            onDispose { displayManager?.unregisterDisplayListener(listener) }
        }
        val lifecycleOwner = LocalLifecycleOwner.current
        DisposableEffect(lifecycleOwner) {
            val observer = LifecycleEventObserver { _, event ->
                if (event == Lifecycle.Event.ON_RESUME) {
                    isScreenMirrored = SecurityUtils.isScreenMirrored(activity)
                }
            }
            lifecycleOwner.lifecycle.addObserver(observer)
            onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
        }

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

        LaunchedEffect(Unit) {
            com.securemed.app.util.GlobalErrorHandler.ztnaBlockedFlow.collect {
                SecurePreferences.isDeviceAuthorized = false
                navController.navigate(Route.DeviceCheck.route) {
                    popUpTo(0) { inclusive = false }
                }
            }
        }

        Scaffold(
            snackbarHost = { androidx.compose.material3.SnackbarHost(snackbarHostState) },
            bottomBar = { BottomNavBar(navController) }
        ) { innerPadding ->
            SecureMedNavHost(
                modifier = Modifier.padding(innerPadding),
                navController = navController,
                startDestination = startDestination,
                openMedications = openMedications,
                authViewModel = authViewModel,
                signOut = signOut
            )
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

        if (isScreenMirrored && SecurePreferences.isScreenMirroringProtectionEnabled && SecurePreferences.isLoggedIn()) {
            ScreenMirrorBlock()
        }

        if (showGlobalBarcodeScanner) {
            BarcodeScannerModal(
                onBarcodeScanned = { rawCode ->
                    showGlobalBarcodeScanner = false
                    val targetId = parsePatientIdFromQr(rawCode)
                    navController.navigate(Route.PatientDetail.createRoute(targetId))
                },
                onDismiss = { showGlobalBarcodeScanner = false }
            )
        }
    }
}

/**
 * Acts on a launcher shortcut (`add_patient`, `scan_barcode`, `break_glass`)
 * and consumes it. Nothing happens when the session is gone: the shortcuts are
 * guarded by login state, so a shortcut tapped at the device-check screen is
 * dropped rather than navigating into an unauthorised screen.
 */
private fun handleShortcutAction(
    action: String?,
    activity: MainActivity,
    navController: androidx.navigation.NavController,
    pendingShortcutAction: MutableStateFlow<String?>,
    onShowScanner: () -> Unit
) {
    when (action) {
        "add_patient" -> {
            if (SecurePreferences.isLoggedIn()) {
                navController.navigate(Route.Patients.route)
            }
            pendingShortcutAction.value = null
        }
        "scan_barcode" -> {
            if (SecurePreferences.isLoggedIn()) {
                onShowScanner()
            }
            pendingShortcutAction.value = null
        }
        "break_glass" -> {
            if (SecurePreferences.isLoggedIn()) {
                NotificationHelper.showEmergencyAlert(
                    activity,
                    title = "تنبيه طوارئ: وصول استثنائي (Break-Glass)",
                    message = "تم تسجيل محاولة وصول استثنائي عاجلة للسجلات الطبية من اختصار النظام."
                )
                navController.navigate(Route.Audit.route)
            }
            pendingShortcutAction.value = null
        }
    }
}

/**
 * The navigation graph. Kept out of [SecureMedAppContent] so the routing table
 * reads as one table, and so the overlay plumbing above it stays declarative.
 */
@Composable
private fun SecureMedNavHost(
    modifier: Modifier,
    navController: androidx.navigation.NavHostController,
    startDestination: String,
    openMedications: Boolean,
    authViewModel: AuthViewModel,
    signOut: (Boolean) -> Unit
) {
    NavHost(
        navController = navController,
        startDestination = startDestination,
        modifier = modifier,
        enterTransition = { slideInHorizontally(initialOffsetX = { 1000 }) + fadeIn() },
        exitTransition = { slideOutHorizontally(targetOffsetX = { -1000 }) + fadeOut() },
        popEnterTransition = { slideInHorizontally(initialOffsetX = { -1000 }) + fadeIn() },
        popExitTransition = { slideOutHorizontally(targetOffsetX = { 1000 }) + fadeOut() }
    ) {
        composable(Route.DeviceCheck.route) {
            DeviceCheckScreen(
                viewModel = authViewModel,
                onDeviceAuthorized = {
                    val destination = when {
                        SecurePreferences.isLoggedIn() && openMedications -> Route.Medications.route
                        SecurePreferences.isLoggedIn() -> Route.Dashboard.route
                        else -> Route.Login.route
                    }
                    navController.navigate(destination) {
                        popUpTo(Route.DeviceCheck.route) { inclusive = true }
                    }
                }
            )
        }
        composable(Route.Login.route) {
            LoginScreen(
                viewModel = authViewModel,
                onLoginSuccess = {
                    // Starts the idle clock. Without it the new session has no
                    // interaction mark at all, and AppLock reads a missing mark
                    // as "idle for an unknown time" — locking the app in the
                    // first seconds after a login.
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
                // Biometric enrollment lives in the profile screen, which is
                // also where Settings was opened from — pop back to it instead
                // of stacking a second copy.
                onNavigateToProfile = {
                    navController.navigate(Route.Profile.route) {
                        popUpTo(Route.Profile.route) { inclusive = true }
                    }
                },
                onLogoutAllDevices = { signOut(true) },
                onAccountDeleted = {
                    // The server deactivated the account and ended every
                    // session; the ViewModel's repository call already wiped
                    // the local side (alarms, Room, tokens, cache). All that
                    // remains here is the route to login.
                    authViewModel.liftAppLockForSignedOut()
                    navController.navigate(Route.DeviceCheck.route) {
                        popUpTo(0) { inclusive = true }
                    }
                }
            )
        }
    }
}

/**
 * Full-screen PHI block shown while the device is casting to an external
 * display, so no patient record reaches a monitor the clinician did not choose.
 */
@Composable
private fun ScreenMirrorBlock() {
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.surface
    ) {
        Box(
            modifier = Modifier.fillMaxSize().padding(32.dp),
            contentAlignment = Alignment.Center
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Icon(
                    Icons.Default.Warning,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.error,
                    modifier = Modifier.size(64.dp)
                )
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    text = "تم رصد بث أو انعكاس للشاشة!",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.error
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "لحماية خصوصية المرضى (HIPAA / PDPL)، يتم حجب عرض السجلات الطبية عند الاتصال بشاشة عرض خارجية.",
                    style = MaterialTheme.typography.bodyMedium,
                    textAlign = androidx.compose.ui.text.style.TextAlign.Center
                )
            }
        }
    }
}

/**
 * Parses standard wristband / emergency card QR payload formats:
 * - SECUREMED-WRISTBAND;ID={id};...
 * - SECUREMED-EMERGENCY;ID={id};...
 * - /patients/{id}
 * - or raw UUID
 */
private fun parsePatientIdFromQr(rawCode: String): String {
    val trimmed = rawCode.trim()
    val idParamRegex = Regex("""(?:ID|PATIENT_ID|PID)=([^;,\s]+)""", RegexOption.IGNORE_CASE)
    val match = idParamRegex.find(trimmed)
    if (match != null) {
        return match.groupValues[1].trim()
    }

    val urlRegex = Regex("""/patients?/([a-f0-9\-]+)""", RegexOption.IGNORE_CASE)
    val urlMatch = urlRegex.find(trimmed)
    if (urlMatch != null) {
        return urlMatch.groupValues[1].trim()
    }

    return trimmed
}
