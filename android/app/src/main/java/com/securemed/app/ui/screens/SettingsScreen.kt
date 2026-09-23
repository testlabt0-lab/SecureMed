package com.securemed.app.ui.screens

import android.content.Context
import android.content.Intent
import android.provider.Settings
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.selection.selectable
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.DarkMode
import androidx.compose.material.icons.filled.DeleteForever
import androidx.compose.material.icons.filled.Devices
import androidx.compose.material.icons.filled.Fingerprint
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.*
import androidx.compose.runtime.*
import com.securemed.app.security.HardwareCryptoManager
import com.securemed.app.security.OverlayDetector
import com.securemed.app.security.NetworkSecurityProbe
import com.securemed.app.security.TamperProofAuditManager
import com.securemed.app.security.MedicalKeyboardHelper
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.securemed.app.BuildConfig
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.data.model.MyDevice
import com.securemed.app.reminders.NotificationHelper
import com.securemed.app.security.AppLock
import com.securemed.app.ui.AuthViewModel
import com.securemed.app.ui.theme.ThemeController

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onBack: () -> Unit,
    onNavigateToProfile: () -> Unit,
    /**
     * Ends every session the account holds, not just this one — the answer to
     * "I lost my phone". Kept out of the ordinary logout button, which must not
     * sign the user out of the workstation they are standing at.
     */
    onLogoutAllDevices: () -> Unit,
    /** The account was deleted server-side; the caller routes to login. */
    onAccountDeleted: () -> Unit
) {
    val context = LocalContext.current

    val darkPreference by ThemeController.darkMode.collectAsState()

    var showThemeDialog by remember { mutableStateOf(false) }
    var showPrivacyDialog by remember { mutableStateOf(false) }
    var showDuressDialog by remember { mutableStateOf(false) }
    var showSecurityAuditDialog by remember { mutableStateOf(false) }

    // Read from AppLock rather than from preferences: it is the single writer of
    // the timeout, and a settings screen left open while the value changes must
    // not keep showing the old one.
    val idleTimeout by AppLock.timeoutMinutes.collectAsState()
    var showTimeoutDialog by remember { mutableStateOf(false) }
    var showLogoutAllDialog by remember { mutableStateOf(false) }
    var showDeleteDialog by remember { mutableStateOf(false) }
    var showDevicesDialog by remember { mutableStateOf(false) }
    val deleteViewModel: DeleteAccountViewModel = hiltViewModel()
    val deleteState by deleteViewModel.uiState.collectAsState()
    val authViewModel: AuthViewModel = hiltViewModel()

    LaunchedEffect(deleteState.deleted) {
        if (deleteState.deleted) {
            onAccountDeleted()
        }
    }

    // POST_NOTIFICATIONS is granted and revoked in system settings, never by
    // the app, so this row mirrors the OS rather than storing a preference of
    // its own. Re-read on every resume: the user may have just changed it in
    // the settings screen we sent them to, and a stale "enabled" here is a
    // promise the app cannot keep for dose reminders.
    var notificationsEnabled by remember { mutableStateOf(NotificationHelper.canNotify(context)) }
    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                notificationsEnabled = NotificationHelper.canNotify(context)
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("الإعدادات") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "رجوع")
                    }
                }
            )
        }
    ) { paddingValues ->
        SettingsList(
            paddingValues = paddingValues,
            darkPreference = darkPreference,
            notificationsEnabled = notificationsEnabled,
            idleTimeout = idleTimeout,
            onNavigateToProfile = onNavigateToProfile,
            onShowThemeDialog = { showThemeDialog = true },
            onOpenNotificationSettings = { openAppNotificationSettings(context) },
            onShowTimeoutDialog = { showTimeoutDialog = true },
            onShowDuressDialog = { showDuressDialog = true },
            onShowSecurityAuditDialog = { showSecurityAuditDialog = true },
            onShowPrivacyDialog = { showPrivacyDialog = true },
            onShowLogoutAllDialog = { showLogoutAllDialog = true },
            onShowDevicesDialog = { showDevicesDialog = true },
            onShowDeleteDialog = {
                deleteViewModel.clearMessage()
                showDeleteDialog = true
            }
        )
    }

    if (showThemeDialog) {
        ThemeSelectionDialog(
            currentMode = darkPreference,
            onSelect = { mode ->
                ThemeController.setThemeMode(mode)
                showThemeDialog = false
            },
            onDismiss = { showThemeDialog = false }
        )
    }

    if (showPrivacyDialog) {
        PrivacyDialog(onDismiss = { showPrivacyDialog = false })
    }

    if (showDuressDialog) {
        DuressPinDialog(onDismiss = { showDuressDialog = false })
    }

    if (showSecurityAuditDialog) {
        SecurityAuditDialog(onDismiss = { showSecurityAuditDialog = false })
    }

    if (showTimeoutDialog) {
        IdleTimeoutDialog(
            currentMinutes = idleTimeout,
            onSelect = { minutes ->
                // Applies to the idle time already accumulated, so picking a
                // shorter period can lock the app on the spot.
                AppLock.setTimeoutMinutes(minutes)
                showTimeoutDialog = false
            },
            onDismiss = { showTimeoutDialog = false }
        )
    }

    if (showLogoutAllDialog) {
        LogoutAllConfirmDialog(
            onConfirm = {
                showLogoutAllDialog = false
                onLogoutAllDevices()
            },
            onDismiss = { showLogoutAllDialog = false }
        )
    }

    // Danger zone: the account-deletion path (Play requirement). Buried at
    // the very end of the settings list on purpose — reachable, never near
    // the routine controls.
    if (showDeleteDialog) {
        DeleteAccountDialog(
            uiState = deleteState,
            onDismiss = {
                if (!deleteState.inProgress) {
                    showDeleteDialog = false
                    deleteViewModel.clearMessage()
                }
            },
            onConfirm = { password -> deleteViewModel.deleteAccount(password) }
        )
    }

    if (showDevicesDialog) {
        MyDevicesDialog(
            authViewModel = authViewModel,
            onDismiss = { showDevicesDialog = false }
        )
    }
}

@Composable
private fun SettingsList(
    paddingValues: PaddingValues,
    darkPreference: Boolean?,
    notificationsEnabled: Boolean,
    idleTimeout: Int,
    onNavigateToProfile: () -> Unit,
    onShowThemeDialog: () -> Unit,
    onOpenNotificationSettings: () -> Unit,
    onShowTimeoutDialog: () -> Unit,
    onShowDuressDialog: () -> Unit,
    onShowSecurityAuditDialog: () -> Unit,
    onShowPrivacyDialog: () -> Unit,
    onShowLogoutAllDialog: () -> Unit,
    onShowDevicesDialog: () -> Unit,
    onShowDeleteDialog: () -> Unit
) {
    var geoEnabled by remember { mutableStateOf(SecurePreferences.isGeoRestrictionEnabled) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(paddingValues),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Text(
                text = "عام",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary
            )
        }
        item {
            val themeModeLabel = when (darkPreference) {
                null -> "حسب النظام (تلقائي مع Material You)"
                true -> "الوضع الداكن"
                false -> "الوضع الفاتح"
            }
            SettingActionItem(
                title = "مظهر التطبيق",
                description = "$themeModeLabel — توافق كامل مع ألوان نظام أندرويد",
                icon = Icons.Default.DarkMode,
                onClick = onShowThemeDialog
            )
        }
        item {
            SettingActionItem(
                title = "الإشعارات",
                description = if (notificationsEnabled) {
                    "✓ مسموح — تنبيهات مواعيد الأدوية تعمل"
                } else {
                    "محجوبة — لن تصل تذكيرات الأدوية. اضغط للسماح"
                },
                icon = Icons.Default.Notifications,
                onClick = onOpenNotificationSettings
            )
        }
        item {
            HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))
        }
        item {
            Text(
                text = "الأمان والخصوصية",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary
            )
        }
        item {
            // Enabling biometric login means enrolling a template with the
            // backend, which needs the account password — that flow lives
            // in the profile screen. A switch here could only flip the
            // local flag, leaving the app claiming an enrollment the
            // server has no record of.
            SettingActionItem(
                title = "تسجيل الدخول بالبصمة",
                description = if (SecurePreferences.biometricEnabled) {
                    "✓ مفعّل — يمكن الإدارة من الملف الشخصي"
                } else {
                    "غير مفعّل — اضغط للتفعيل من الملف الشخصي"
                },
                icon = Icons.Default.Fingerprint,
                onClick = onNavigateToProfile
            )
        }
        item {
            // The one security setting the user is allowed to weaken, and
            // only within a range — see AppLock.TIMEOUT_CHOICES_MINUTES.
            SettingActionItem(
                title = "القفل التلقائي للعدم النشاط",
                description = "يُقفل التطبيق بعد ${minutesLabel(idleTimeout)} من عدم الاستخدام، " +
                    "ويُطلب بعدها التعرّف على البصمة أو رمز الجهاز",
                icon = Icons.Default.Lock,
                onClick = onShowTimeoutDialog
            )
        }
        item {
            var autoLockBg by remember { mutableStateOf(SecurePreferences.autoLockOnBackground) }
            SettingToggleItem(
                title = "القفل التلقائي السريع عند الخروج (دقيقة)",
                description = "قفل التطبيق فوراً عند البقاء في الخلفية لأكثر من دقيقة لحماية السجلات الطبية",
                icon = Icons.Default.Lock,
                checked = autoLockBg,
                onCheckedChange = {
                    SecurePreferences.autoLockOnBackground = it
                    autoLockBg = it
                }
            )
        }
        item {
            var screenshotProtected by remember { mutableStateOf(SecurePreferences.isScreenshotProtectionEnabled) }
            SettingToggleItem(
                title = "حظر لقطات الشاشة وستارة الخصوصية",
                description = "منع تصوير الشاشة وحجب المحتوى في قائمة التطبيقات الحديثة (Recent Apps)",
                icon = Icons.Default.Security,
                checked = screenshotProtected,
                onCheckedChange = {
                    SecurePreferences.isScreenshotProtectionEnabled = it
                    screenshotProtected = it
                }
            )
        }
        item {
            var watermarkEnabled by remember { mutableStateOf(SecurePreferences.isWatermarkEnabled) }
            SettingToggleItem(
                title = "العلامة المائية الرقمية الحية (Dynamic Watermark)",
                description = "إظهار هوية المستخدم والوقت في خلفية السجلات الطبية لمنع التصوير الخارجي",
                icon = Icons.Default.Visibility,
                checked = watermarkEnabled,
                onCheckedChange = {
                    SecurePreferences.isWatermarkEnabled = it
                    watermarkEnabled = it
                }
            )
        }
        item {
            var screenMirroringEnabled by remember { mutableStateOf(SecurePreferences.isScreenMirroringProtectionEnabled) }
            SettingToggleItem(
                title = "حظر بث الشاشة وانعكاسها (Screen Mirroring)",
                description = "حجب السجلات الطبية فوراً عند محاولة بث الشاشة إلى جهاز عرض خارجي",
                icon = Icons.Default.Devices,
                checked = screenMirroringEnabled,
                onCheckedChange = {
                    SecurePreferences.isScreenMirroringProtectionEnabled = it
                    screenMirroringEnabled = it
                }
            )
        }
        item {
            var clipboardAutoClear by remember { mutableStateOf(SecurePreferences.isClipboardAutoClearEnabled) }
            SettingToggleItem(
                title = "التنظيف التلقائي للحافظة (Clipboard Sanitizer)",
                description = "مسح النصوص الطبية المنسوخة تلقائياً بعد 30 ثانية وعند الخروج من التطبيق",
                icon = Icons.Default.Shield,
                checked = clipboardAutoClear,
                onCheckedChange = {
                    SecurePreferences.isClipboardAutoClearEnabled = it
                    clipboardAutoClear = it
                }
            )
        }
        item {
            SettingActionItem(
                title = "رمز الطوارئ والإلغاء القسري (Duress PIN)",
                description = if (!SecurePreferences.duressPin.isNullOrBlank()) {
                    "✓ مفعّل — يمسح البيانات صامتاً عند إدخاله في شاشة القفل"
                } else {
                    "غير محدد — اضغط لتعيين رمز الطوارئ البديل"
                },
                icon = Icons.Default.WarningAmber,
                onClick = onShowDuressDialog
            )
        }
        item {
            SettingToggleItem(
                title = "الحماية الجغرافية للبيانات (Geofencing)",
                description = "قفل السجلات الحساسة تلقائياً خارج النطاق الجغرافي للمستشفى",
                icon = Icons.Default.LocationOn,
                checked = geoEnabled,
                onCheckedChange = {
                    SecurePreferences.isGeoRestrictionEnabled = it
                    geoEnabled = it
                }
            )
        }
        item {
            SettingActionItem(
                title = "فحص أمان الجهاز وسجل التدقيق المشفر",
                description = "فحص عتاد التشفير (StrongBox)، النوافذ العائمة، وسلامة سلسلة التدقيق",
                icon = Icons.Default.Shield,
                onClick = onShowSecurityAuditDialog
            )
        }
        item {
            SettingActionItem(
                title = "حماية البيانات",
                description = "كيف يحمي التطبيق بياناتك الطبية",
                icon = Icons.Default.Security,
                onClick = onShowPrivacyDialog
            )
        }
        item {
            SettingActionItem(
                title = "تسجيل الخروج من كل الأجهزة",
                description = "ينهي الجلسة هنا وعلى كل جهاز آخر — لحالة فقدان الهاتف",
                icon = Icons.AutoMirrored.Filled.Logout,
                onClick = onShowLogoutAllDialog
            )
        }
        item {
            SettingActionItem(
                title = "أجهزتي المسجلة",
                description = "اعرض الأجهزة الموثوقة بحسابك وأزل أي جهاز لم تعد تستخدمه",
                icon = Icons.Default.Devices,
                onClick = onShowDevicesDialog
            )
        }
        item {
            HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))
        }
        item {
            SettingActionItem(
                title = "حذف الحساب",
                description = "تعطيل نهائي للحساب وإنهاء كل جلساته — يتطلب كلمة المرور",
                icon = Icons.Default.DeleteForever,
                onClick = onShowDeleteDialog
            )
        }
        item {
            Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                Text(
                    text = "الإصدار ${BuildConfig.VERSION_NAME} (SecureMed)",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun ThemeSelectionDialog(
    currentMode: Boolean?,
    onSelect: (Boolean?) -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        icon = { Icon(Icons.Default.DarkMode, contentDescription = null) },
        title = { Text("اختيار مظهر التطبيق", fontWeight = FontWeight.Bold) },
        text = {
            Column {
                listOf(
                    Triple(false, "الوضع الفاتح", "مظهر ناصع ومشرق"),
                    Triple(true, "الوضع الداكن", "مظهر داكن ومريح للعين"),
                    Triple(null, "حسب النظام (تلقائي)", "يتوافق مع سمة النظام وألوان Material You")
                ).forEach { (mode, title, desc) ->
                    val selected = currentMode == mode
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .selectable(
                                selected = selected,
                                role = Role.RadioButton,
                                onClick = { onSelect(mode) }
                            )
                            .padding(vertical = 10.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        RadioButton(selected = selected, onClick = null)
                        Spacer(modifier = Modifier.width(12.dp))
                        Column {
                            Text(text = title, style = MaterialTheme.typography.bodyLarge)
                            Text(
                                text = desc,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text("إلغاء") }
        }
    )
}

@Composable
private fun PrivacyDialog(onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        icon = { Icon(Icons.Default.Security, contentDescription = null) },
        title = { Text("حماية البيانات") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                PrivacyPoint("قاعدة البيانات على الجهاز مشفَّرة بـ SQLCipher (AES-256).")
                PrivacyPoint("رموز الدخول محفوظة في EncryptedSharedPreferences.")
                PrivacyPoint("كل اتصال بالخادم عبر HTTPS مع تثبيت الشهادة (Certificate Pinning).")
                PrivacyPoint("لقطات الشاشة وتسجيلها ممنوعة داخل التطبيق مع ستارة الخصوصية.")
                PrivacyPoint("إشعارات الأدوية تُخفي التفاصيل على شاشة القفل.")
                PrivacyPoint("تفريغ تلقائي للحافظة لمنع تسريب أرقام المرضى.")
                PrivacyPoint("حماية الشاشة من التنصت والنوافذ العائمة (Anti-Tapjacking).")
                PrivacyPoint("سجل تدقيق محلي مشفر ومحكم التجزئة غير قابل للتلاعب.")
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text("حسناً") }
        }
    )
}

@Composable
private fun DuressPinDialog(onDismiss: () -> Unit) {
    var tempPin by remember { mutableStateOf(SecurePreferences.duressPin ?: "") }
    AlertDialog(
        onDismissRequest = onDismiss,
        icon = { Icon(Icons.Default.WarningAmber, contentDescription = null, tint = MaterialTheme.colorScheme.error) },
        title = { Text("رمز الطوارئ (Duress PIN)") },
        text = {
            Column {
                Text(
                    "في حال إجبارك على فتح الهاتف تحت التهديد أو سرقته، إدخال هذا الرمز " +
                        "البديل بدلاً من رمزك المعتاد في شاشة القفل سيؤدي فوراً وبشكل صامت " +
                        "إلى مسح جميع البيانات المشفرة وإسقاط الجلسة تماماً دون إشعار المهاجم.",
                    style = MaterialTheme.typography.bodySmall
                )
                Spacer(modifier = Modifier.height(12.dp))
                OutlinedTextField(
                    value = tempPin,
                    onValueChange = { tempPin = it },
                    label = { Text("رمز الطوارئ (4 أرقام أو أكثر)") },
                    singleLine = true,
                    keyboardOptions = MedicalKeyboardHelper.securePin(),
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    SecurePreferences.duressPin = tempPin.takeIf { it.isNotBlank() }
                    onDismiss()
                },
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
            ) {
                Text("حفظ رمز الطوارئ")
            }
        },
        dismissButton = {
            TextButton(onClick = {
                SecurePreferences.duressPin = null
                onDismiss()
            }) {
                Text("تعطيل الرمز")
            }
        }
    )
}

@Composable
private fun SecurityAuditDialog(onDismiss: () -> Unit) {
    val context = LocalContext.current
    val hwSecurity = remember { HardwareCryptoManager.getHardwareSecurityLevel(context) }
    val netSecurity = remember { NetworkSecurityProbe.assessNetworkSecurity(context) }
    val overlayRisks = remember { OverlayDetector.scanForRisks(context) }
    val auditIntegrity = remember { TamperProofAuditManager.verifyChainIntegrity(context) }
    val auditCount = remember { TamperProofAuditManager.getEventCount(context) }

    AlertDialog(
        onDismissRequest = onDismiss,
        icon = { Icon(Icons.Default.Shield, contentDescription = null, tint = MaterialTheme.colorScheme.primary) },
        title = { Text("لوحة الفحص الأمني للجهاز", fontWeight = FontWeight.Bold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("🛡️ التشفير العتادي: $hwSecurity", style = MaterialTheme.typography.bodyMedium)
                Text(
                    text = if (netSecurity.isSecure) "🌐 شبكة الاتصال: آمنة ومشفرة"
                           else "⚠️ تحذير شبكة: ${netSecurity.warningMessage}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = if (netSecurity.isSecure) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.error
                )
                Text(
                    text = if (overlayRisks.isEmpty()) "✓ النوافذ العائمة: لا توجد نوافذ تنصت أو تطفل نشطة"
                           else "⚠️ رُصدت خدمات وصول مشبوهة: ${overlayRisks.size}",
                    style = MaterialTheme.typography.bodyMedium
                )
                Text(
                    text = if (auditIntegrity.first) "🔒 سلسلة التدقيق المشفرة: سليمة 100% ($auditCount حدث مسجل)"
                           else "❌ خلل في السلسلة: تم رصد تلاعب عند الحدث #${auditIntegrity.second}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = if (auditIntegrity.first) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
                )
            }
        },
        confirmButton = {
            Button(onClick = onDismiss) { Text("إغلاق") }
        }
    )
}

@Composable
private fun IdleTimeoutDialog(
    currentMinutes: Int,
    onSelect: (Int) -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        icon = { Icon(Icons.Default.Lock, contentDescription = null) },
        title = { Text("مدة القفل التلقائي") },
        text = {
            Column {
                Text(
                    text = "لا يمكن تعطيل القفل — البيانات المعروضة سجلات مرضى.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(bottom = 8.dp)
                )
                AppLock.TIMEOUT_CHOICES_MINUTES.forEach { minutes ->
                    val selected = minutes == currentMinutes
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            // selectable (not clickable) so the whole row is
                            // one radio target for TalkBack instead of a
                            // button beside an unlabelled control.
                            .selectable(
                                selected = selected,
                                role = Role.RadioButton,
                                onClick = { onSelect(minutes) }
                            )
                            .padding(vertical = 12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        RadioButton(selected = selected, onClick = null)
                        Spacer(modifier = Modifier.width(12.dp))
                        Text(
                            text = minutesLabel(minutes),
                            style = MaterialTheme.typography.bodyLarge
                        )
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text("إلغاء") }
        }
    )
}

@Composable
private fun LogoutAllConfirmDialog(
    onConfirm: () -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        icon = { Icon(Icons.AutoMirrored.Filled.Logout, contentDescription = null) },
        title = { Text("تسجيل الخروج من كل الأجهزة؟") },
        text = {
            Text(
                "ستنتهي الجلسة على هذا الجهاز وعلى كل جهاز آخر مسجَّل بهذا الحساب، " +
                    "بما في ذلك أجهزة الحاسب. لا يمكن التراجع عن هذا الإجراء."
            )
        },
        confirmButton = {
            TextButton(onClick = onConfirm) {
                Text("تسجيل الخروج", color = MaterialTheme.colorScheme.error)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("إلغاء") }
        }
    )
}

/**
 * Arabic reading of a minute count. Written as a rule rather than a lookup so it
 * stays correct if [AppLock.TIMEOUT_CHOICES_MINUTES] gains a value: 3-10 take the
 * plural (دقائق) and 11 upwards return to the singular (دقيقة).
 */
private fun minutesLabel(minutes: Int): String = when {
    minutes == 1 -> "دقيقة واحدة"
    minutes == 2 -> "دقيقتين"
    minutes in 3..10 -> "$minutes دقائق"
    else -> "$minutes دقيقة"
}

/**
 * "أجهزتي المسجلة": reads the trusted-device registry and offers self-service
 * removal — سحب الثقة وإنهاء الجلسة دون قائمة سوداء (يمكن طلب التفعيل مجدداً).
 * The device making this call can remove itself too, which acts as a local
 * "log out of this device permanently".
 */
@Composable
private fun MyDevicesDialog(
    authViewModel: AuthViewModel,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    var devices by remember { mutableStateOf<List<MyDevice>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var removingFp by remember { mutableStateOf<String?>(null) }
    var message by remember { mutableStateOf<String?>(null) }

    fun refresh() {
        loading = true
        authViewModel.loadMyDevices { list ->
            devices = list
            loading = false
        }
    }
    LaunchedEffect(Unit) { refresh() }

    AlertDialog(
        onDismissRequest = onDismiss,
        icon = { Icon(Icons.Default.Devices, contentDescription = null) },
        title = { Text("أجهزتي المسجلة", fontWeight = FontWeight.Bold) },
        text = {
            Column {
                when {
                    loading -> CircularProgressIndicator(
                        modifier = Modifier.size(32.dp)
                    )
                    devices.isEmpty() -> Text(
                        "لا توجد أجهزة مسجلة بحسابك بعد.",
                        style = MaterialTheme.typography.bodyMedium
                    )
                    else -> Column {
                        devices.forEach { device ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 6.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = device.osInfo?.takeIf { it.isNotBlank() }
                                            ?: "جهاز غير معروف",
                                        style = MaterialTheme.typography.bodyMedium,
                                        fontWeight = FontWeight.SemiBold
                                    )
                                    Text(
                                        text = buildString {
                                            append(device.deviceFingerprint.take(16))
                                            device.lastIpAddress?.let {
                                                append(" • ")
                                                append(it)
                                            }
                                        },
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                    if (device.isTrusted) {
                                        Text(
                                            "✓ موثوق",
                                            style = MaterialTheme.typography.labelSmall,
                                            color = MaterialTheme.colorScheme.primary
                                        )
                                    }
                                }
                                TextButton(
                                    onClick = {
                                        removingFp = device.deviceFingerprint
                                        authViewModel.removeMyDeviceByFingerprint(
                                            device.deviceFingerprint
                                        ) { ok, msg ->
                                            removingFp = null
                                            message = msg
                                            if (ok) {
                                                if (device.deviceFingerprint ==
                                                    com.securemed.app.security.SecurityUtils
                                                        .getDeviceFingerprint(context)
                                                ) {
                                                    onDismiss()
                                                } else {
                                                    refresh()
                                                }
                                            }
                                        }
                                    },
                                    enabled = removingFp == null
                                ) {
                                    Text(
                                        "إزالة",
                                        color = MaterialTheme.colorScheme.error
                                    )
                                }
                            }
                            HorizontalDivider()
                        }
                        message?.let {
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(
                                it,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.primary
                            )
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            "إزالة جهاز تسحب ثقته وتنتهي جلسته، دون حظره — " +
                                "يمكن طلب تفعيله مجدداً لاحقاً.",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text("إغلاق") }
        }
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DeleteAccountDialog(
    uiState: DeleteAccountUiState,
    onDismiss: () -> Unit,
    onConfirm: (password: String) -> Unit
) {
    var password by remember { mutableStateOf("") }
    var passwordVisible by remember { mutableStateOf(false) }
    var validationError by remember { mutableStateOf<String?>(null) }

    AlertDialog(
        onDismissRequest = onDismiss,
        icon = { Icon(Icons.Default.DeleteForever, contentDescription = null, tint = MaterialTheme.colorScheme.error) },
        title = { Text("حذف الحساب", fontWeight = FontWeight.Bold) },
        text = {
            Column {
                Text(
                    "سيُعطَّل الحساب نهائياً وتنتهي كل جلساته على كل الأجهزة. " +
                        "سجلات المرضى الطبية تبقى محفوظة في النظام وفق سياسة الاحتفاظ. " +
                        "لا يمكن التراجع عن هذا الإجراء.",
                    style = MaterialTheme.typography.bodyMedium
                )
                Spacer(modifier = Modifier.height(12.dp))
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    label = { Text("أدخل كلمة المرور للتأكيد") },
                    visualTransformation = if (passwordVisible) VisualTransformation.None
                    else PasswordVisualTransformation(),
                    trailingIcon = {
                        IconButton(onClick = { passwordVisible = !passwordVisible }) {
                            Icon(
                                if (passwordVisible) Icons.Default.Visibility else Icons.Default.VisibilityOff,
                                contentDescription = if (passwordVisible) "إخفاء كلمة المرور" else "إظهار كلمة المرور"
                            )
                        }
                    },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                uiState.message?.let {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                }
                validationError?.let {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                }
            }
        },
        confirmButton = {
            if (uiState.inProgress) {
                CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
            } else {
                Button(
                    onClick = {
                        if (password.isBlank()) validationError = "أدخل كلمة المرور"
                        else {
                            validationError = null
                            onConfirm(password)
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                ) { Text("حذف نهائي") }
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss, enabled = !uiState.inProgress) { Text("إلغاء") }
        }
    )
}

@Composable
private fun PrivacyPoint(text: String) {
    Row {
        Text("•  ", style = MaterialTheme.typography.bodyMedium)
        Text(text, style = MaterialTheme.typography.bodyMedium)
    }
}

/**
 * Opens this app's page in the system notification settings. The app cannot
 * grant POST_NOTIFICATIONS itself once the user has denied it, so sending
 * them here is the only way back to working dose reminders.
 */
private fun openAppNotificationSettings(context: Context) {
    runCatching {
        context.startActivity(
            Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
                .putExtra(Settings.EXTRA_APP_PACKAGE, context.packageName)
        )
    }.onFailure {
        // Some OEM builds ship no notification settings activity; the app
        // details page always exists and gets the user to the same toggle.
        runCatching {
            context.startActivity(
                Intent(
                    Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    android.net.Uri.fromParts("package", context.packageName, null)
                )
            )
        }
    }
}

@Composable
fun SettingToggleItem(
    title: String,
    description: String,
    icon: ImageVector,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.size(24.dp)
        )
        Spacer(modifier = Modifier.width(16.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(text = title, style = MaterialTheme.typography.bodyLarge)
            Text(text = description, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange
        )
    }
}

@Composable
fun SettingActionItem(
    title: String,
    description: String,
    icon: ImageVector,
    onClick: () -> Unit
) {
    Surface(
        onClick = onClick,
        color = androidx.compose.ui.graphics.Color.Transparent
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(24.dp)
            )
            Spacer(modifier = Modifier.width(16.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(text = title, style = MaterialTheme.typography.bodyLarge)
                Text(text = description, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}
