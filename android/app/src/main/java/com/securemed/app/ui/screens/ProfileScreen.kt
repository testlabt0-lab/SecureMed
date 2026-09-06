package com.securemed.app.ui.screens

import android.os.Build
import androidx.compose.foundation.background
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.DarkMode
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Fingerprint
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.fragment.app.FragmentActivity
import androidx.hilt.navigation.compose.hiltViewModel
import coil.compose.AsyncImage
import coil.request.ImageRequest
import com.securemed.app.auth.BiometricManager
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.ui.AuthUiState
import com.securemed.app.ui.AuthViewModel
import com.securemed.app.ui.theme.ThemeController

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileScreen(
    onLogout: () -> Unit,
    onBack: () -> Unit,
    onNavigateToSettings: () -> Unit,
    authViewModel: AuthViewModel = hiltViewModel()
) {
    val context = LocalContext.current
    val biometricManager = remember { BiometricManager(context) }
    val isBiometricAvailable = remember { biometricManager.isBiometricAvailable() }
    var showEnrollDialog by remember { mutableStateOf(false) }
    var statusMessage by remember { mutableStateOf<String?>(null) }

    /**
     * Enrollment state as this screen sees it. It has to be Compose state:
     * reading `SecurePreferences.biometricEnabled` directly, as every branch below
     * used to, gives a value Compose cannot observe, so the row kept saying
     * "اضغط للتفعيل" after a successful enrollment until something else forced a
     * recomposition.
     */
    var biometricEnabled by remember { mutableStateOf(SecurePreferences.biometricEnabled) }

    val authState by authViewModel.uiState.collectAsState()
    val authError by authViewModel.errorMessage.collectAsState()

    // The server is the only authority on whether this device is enrolled, so the
    // outcome is reported from its answer — not from the prompt closing.
    LaunchedEffect(authState) {
        when (authState) {
            is AuthUiState.BiometricEnrolled -> {
                biometricEnabled = true
                statusMessage = "✓ تم تسجيل البصمة على هذا الجهاز"
                authViewModel.resetState()
            }
            is AuthUiState.Error -> {
                statusMessage = "❌ فشل تسجيل البصمة: ${authError ?: "خطأ غير معروف"}"
                authViewModel.resetState()
            }
            else -> Unit
        }
    }

    // Theme preference: null = follow the system
    val darkPreference by ThemeController.darkMode.collectAsState()
    val isDarkTheme = darkPreference ?: isSystemInDarkTheme()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("الملف الشخصي") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "رجوع")
                    }
                },
                actions = {
                    // The app's only way into the settings screen — it was
                    // registered in the NavHost with nothing navigating to it.
                    IconButton(onClick = onNavigateToSettings) {
                        Icon(Icons.Default.Settings, "الإعدادات")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // User card
            Card(
                modifier = Modifier.fillMaxWidth(),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(20.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    AsyncImage(
                        model = ImageRequest.Builder(LocalContext.current)
                            .data("https://ui-avatars.com/api/?name=${SecurePreferences.userName ?: "U"}&background=random")
                            .crossfade(true)
                            .build(),
                        contentDescription = "صورة الملف الشخصي",
                        modifier = Modifier
                            .size(64.dp)
                            .background(MaterialTheme.colorScheme.primary, RoundedCornerShape(20.dp))
                    )
                    Spacer(modifier = Modifier.width(16.dp))
                    Column {
                        Text(
                            text = SecurePreferences.userName ?: "—",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = SecurePreferences.userEmail ?: "—",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = "الدور: ${SecurePreferences.userRole ?: "—"}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            // Security section
            Card(
                modifier = Modifier.fillMaxWidth(),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Shield, null, tint = MaterialTheme.colorScheme.primary)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            "إعدادات الأمان",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    Spacer(modifier = Modifier.height(12.dp))

                    // Biometric toggle
                    Surface(
                        onClick = {
                            if (isBiometricAvailable && !biometricEnabled) {
                                showEnrollDialog = true
                            }
                        },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f)
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                Icons.Default.Fingerprint,
                                null,
                                tint = if (biometricEnabled)
                                    MaterialTheme.colorScheme.secondary
                                else MaterialTheme.colorScheme.outline
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    "المصادقة البيومترية",
                                    style = MaterialTheme.typography.bodyLarge,
                                    fontWeight = FontWeight.Medium
                                )
                                Text(
                                    text = if (!isBiometricAvailable) "البصمة غير متاحة على هذا الجهاز"
                                    else if (biometricEnabled) "✓ مفعلة"
                                    else "اضغط للتفعيل",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = if (biometricEnabled)
                                        MaterialTheme.colorScheme.secondary
                                    else MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            if (biometricEnabled) {
                                Text(
                                    "✓",
                                    color = MaterialTheme.colorScheme.secondary,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    // Dark mode toggle
                    Surface(
                        onClick = { ThemeController.setDarkMode(!isDarkTheme) },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f)
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                Icons.Default.DarkMode,
                                null,
                                tint = if (isDarkTheme) MaterialTheme.colorScheme.primary
                                else MaterialTheme.colorScheme.outline
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    "الوضع الداكن",
                                    style = MaterialTheme.typography.bodyLarge,
                                    fontWeight = FontWeight.Medium
                                )
                                Text(
                                    text = if (isDarkTheme) "مفعل" else "غير مفعل",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            Switch(
                                checked = isDarkTheme,
                                onCheckedChange = { ThemeController.setDarkMode(it) }
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    // Other security items
                    ProfileInfoItem(
                        icon = Icons.Default.Lock,
                        title = "كلمة المرور",
                        subtitle = "آخر تغيير: غير معروف"
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    ProfileInfoItem(
                        icon = Icons.Default.Shield,
                        title = "WAF Protection",
                        subtitle = "✓ نشط"
                    )
                }
            }

            // Account info
            Card(
                modifier = Modifier.fillMaxWidth(),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        "معلومات الحساب",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    InfoRow(icon = Icons.Default.Email, label = "البريد", value = SecurePreferences.userEmail ?: "—")
                    InfoRow(icon = Icons.Default.Person, label = "اسم المستخدم", value = SecurePreferences.userName ?: "—")
                    InfoRow(icon = Icons.Default.Shield, label = "الدور", value = SecurePreferences.userRole ?: "—")
                    InfoRow(icon = Icons.Default.Fingerprint, label = "معرف الجهاز", value = SecurePreferences.deviceId.take(20) + "...")
                }
            }

            statusMessage?.let {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer
                    )
                ) {
                    Text(
                        text = it,
                        modifier = Modifier.padding(16.dp)
                    )
                }
            }

            // Logout button
            Spacer(modifier = Modifier.weight(1f))
            Button(
                onClick = onLogout,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.error,
                    contentColor = MaterialTheme.colorScheme.onError
                )
            ) {
                Text("تسجيل الخروج")
            }
        }
    }

    // Biometric Enrollment Dialog
    if (showEnrollDialog) {
        AlertDialog(
            onDismissRequest = { showEnrollDialog = false },
            title = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Fingerprint, null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("تسجيل البصمة")
                }
            },
            text = {
                Column {
                    Text(
                        "تُنشئ البصمة مفتاحاً خاصاً داخل مخزن مفاتيح الجهاز؛ " +
                        "لا تُرسل بصمتك ولا أي صورة عنها إلى الخادم، بل المفتاح العام فقط."
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        "اضغط «متابعة» ثم ضع إصبعك على المستشعر.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        showEnrollDialog = false
                        val activity = context as? FragmentActivity
                        if (activity == null) {
                            statusMessage = "❌ تعذر عرض نافذة البصمة"
                        } else {
                            biometricManager.authenticate(
                                activity = activity,
                                title = "تسجيل البصمة",
                                subtitle = "SecureMed",
                                description = "ضع إصبعك على المستشعر لتسجيل بصمتك",
                                // No CryptoObject: the key does not exist yet, and
                                // this prompt is only a presence check. What the
                                // server trusts at enrollment is the authenticated
                                // session, and thereafter the fact that the key it
                                // registered cannot sign without a finger.
                                cryptoObject = null,
                                onSuccess = {
                                    // This used to set `biometricEnabled = true`
                                    // and report success without sending anything
                                    // anywhere. The server never learned of the
                                    // device, so the login screen then offered a
                                    // fingerprint button that could not work.
                                    statusMessage = "جارٍ تسجيل الجهاز…"
                                    authViewModel.enrollBiometric(deviceLabel())
                                },
                                onError = { error ->
                                    statusMessage = "❌ فشل: $error"
                                },
                                onCancel = {
                                    statusMessage = "تم إلغاء التسجيل"
                                }
                            )
                        }
                    }
                ) { Text("متابعة") }
            },
            dismissButton = {
                TextButton(onClick = { showEnrollDialog = false }) {
                    Text("إلغاء")
                }
            }
        )
    }
}

/**
 * How this phone is labelled in the account's device list on the server.
 *
 * A name only, for the user's benefit when revoking a device. Identity is the
 * `device_id` in [SecurePreferences], which is stable and survives logout.
 */
private fun deviceLabel(): String =
    listOf(Build.MANUFACTURER, Build.MODEL)
        .filter { it.isNotBlank() }
        .joinToString(" ")
        .ifBlank { "جهاز أندرويد" }

@Composable
private fun ProfileInfoItem(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String,
    subtitle: String
) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            icon,
            null,
            tint = MaterialTheme.colorScheme.outline,
            modifier = Modifier.size(20.dp)
        )
        Spacer(modifier = Modifier.width(12.dp))
        Column {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyMedium
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun InfoRow(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    label: String,
    value: String
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, null, tint = MaterialTheme.colorScheme.outline, modifier = Modifier.size(18.dp))
        Spacer(modifier = Modifier.width(12.dp))
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.weight(1f)
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodySmall,
            fontWeight = FontWeight.Medium
        )
    }
}
