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
import androidx.compose.material.icons.filled.Fingerprint
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Security
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.securemed.app.BuildConfig
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.reminders.NotificationHelper
import com.securemed.app.security.AppLock
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
    onLogoutAllDevices: () -> Unit
) {
    val context = LocalContext.current

    val darkPreference by ThemeController.darkMode.collectAsState()
    val isDarkTheme = darkPreference ?: isSystemInDarkTheme()

    var showPrivacyDialog by remember { mutableStateOf(false) }

    // Read from AppLock rather than from preferences: it is the single writer of
    // the timeout, and a settings screen left open while the value changes must
    // not keep showing the old one.
    val idleTimeout by AppLock.timeoutMinutes.collectAsState()
    var showTimeoutDialog by remember { mutableStateOf(false) }
    var showLogoutAllDialog by remember { mutableStateOf(false) }

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
                SettingToggleItem(
                    title = "الوضع الداكن",
                    description = "مظهر داكن يريح العين في الإضاءة المنخفضة",
                    icon = Icons.Default.DarkMode,
                    checked = isDarkTheme,
                    onCheckedChange = { ThemeController.setDarkMode(it) }
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
                    onClick = { openAppNotificationSettings(context) }
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
                    title = "القفل التلقائي",
                    description = "يُقفل التطبيق بعد ${minutesLabel(idleTimeout)} من عدم الاستخدام، " +
                        "ويُطلب بعدها التعرّف على البصمة أو رمز الجهاز",
                    icon = Icons.Default.Lock,
                    onClick = { showTimeoutDialog = true }
                )
            }
            item {
                SettingActionItem(
                    title = "حماية البيانات",
                    description = "كيف يحمي التطبيق بياناتك الطبية",
                    icon = Icons.Default.Security,
                    onClick = { showPrivacyDialog = true }
                )
            }
            item {
                SettingActionItem(
                    title = "تسجيل الخروج من كل الأجهزة",
                    description = "ينهي الجلسة هنا وعلى كل جهاز آخر — لحالة فقدان الهاتف",
                    icon = Icons.AutoMirrored.Filled.Logout,
                    onClick = { showLogoutAllDialog = true }
                )
            }
            item {
                HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))
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

    if (showPrivacyDialog) {
        AlertDialog(
            onDismissRequest = { showPrivacyDialog = false },
            icon = { Icon(Icons.Default.Security, contentDescription = null) },
            title = { Text("حماية البيانات") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    PrivacyPoint("قاعدة البيانات على الجهاز مشفَّرة بـ SQLCipher (AES-256).")
                    PrivacyPoint("رموز الدخول محفوظة في EncryptedSharedPreferences.")
                    PrivacyPoint("كل اتصال بالخادم عبر HTTPS مع تثبيت الشهادة (Certificate Pinning).")
                    PrivacyPoint("لقطات الشاشة وتسجيلها ممنوعة داخل التطبيق.")
                    PrivacyPoint("إشعارات الأدوية تُخفي التفاصيل على شاشة القفل.")
                    PrivacyPoint("بيانات المرضى المخزَّنة تُحذف من الجهاز عند تسجيل الخروج.")
                    PrivacyPoint("كل وصول للسجلات الطبية يُسجَّل في سجل التدقيق على الخادم.")
                }
            },
            confirmButton = {
                TextButton(onClick = { showPrivacyDialog = false }) { Text("حسناً") }
            }
        )
    }

    if (showTimeoutDialog) {
        AlertDialog(
            onDismissRequest = { showTimeoutDialog = false },
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
                        val selected = minutes == idleTimeout
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                // selectable (not clickable) so the whole row is
                                // one radio target for TalkBack instead of a
                                // button beside an unlabelled control.
                                .selectable(
                                    selected = selected,
                                    role = Role.RadioButton,
                                    onClick = {
                                        // Applies to the idle time already
                                        // accumulated, so picking a shorter
                                        // period can lock the app on the spot.
                                        AppLock.setTimeoutMinutes(minutes)
                                        showTimeoutDialog = false
                                    }
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
                TextButton(onClick = { showTimeoutDialog = false }) { Text("إلغاء") }
            }
        )
    }

    if (showLogoutAllDialog) {
        AlertDialog(
            onDismissRequest = { showLogoutAllDialog = false },
            icon = { Icon(Icons.AutoMirrored.Filled.Logout, contentDescription = null) },
            title = { Text("تسجيل الخروج من كل الأجهزة؟") },
            text = {
                Text(
                    "ستنتهي الجلسة على هذا الجهاز وعلى كل جهاز آخر مسجَّل بهذا الحساب، " +
                        "بما في ذلك أجهزة الحاسب. لا يمكن التراجع عن هذا الإجراء."
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        showLogoutAllDialog = false
                        onLogoutAllDevices()
                    }
                ) {
                    Text("تسجيل الخروج", color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = {
                TextButton(onClick = { showLogoutAllDialog = false }) { Text("إلغاء") }
            }
        )
    }
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
