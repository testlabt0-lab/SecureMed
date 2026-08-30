package com.securemed.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Fingerprint
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.fragment.app.FragmentActivity
import com.securemed.app.auth.BiometricManager
import com.securemed.app.data.local.SecurePreferences

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileScreen(
    onLogout: () -> Unit,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val biometricManager = remember { BiometricManager(context) }
    val isBiometricAvailable = remember { biometricManager.isBiometricAvailable() }
    var showEnrollDialog by remember { mutableStateOf(false) }
    var statusMessage by remember { mutableStateOf<String?>(null) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("الملف الشخصي") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, "رجوع")
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
                    Box(
                        modifier = Modifier
                            .size(64.dp)
                            .background(
                                MaterialTheme.colorScheme.primary,
                                RoundedCornerShape(20.dp)
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = SecurePreferences.userName?.firstOrNull()?.toString() ?: "?",
                            style = MaterialTheme.typography.headlineMedium,
                            color = MaterialTheme.colorScheme.onPrimary,
                            fontWeight = FontWeight.Bold
                        )
                    }
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
                            if (isBiometricAvailable && !SecurePreferences.biometricEnabled) {
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
                                tint = if (SecurePreferences.biometricEnabled)
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
                                    else if (SecurePreferences.biometricEnabled) "✓ مفعلة"
                                    else "اضغط للتفعيل",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = if (SecurePreferences.biometricEnabled)
                                        MaterialTheme.colorScheme.secondary
                                    else MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            if (SecurePreferences.biometricEnabled) {
                                Text(
                                    "✓",
                                    color = MaterialTheme.colorScheme.secondary,
                                    fontWeight = FontWeight.Bold
                                )
                            }
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
                        "سيتم تسجيل بصمتك بشكل آمن. لن يتم تخزين البصمة الأصلية، " +
                        "بل سيتم تخزين hash مشفر فقط (SHA-256 + salt)."
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
                        activity?.let {
                            biometricManager.authenticate(
                                activity = it,
                                title = "تسجيل البصمة",
                                subtitle = "SecureMed",
                                description = "ضع إصبعك على المستشعر لتسجيل بصمتك",
                                onSuccess = { template ->
                                    SecurePreferences.biometricEnabled = true
                                    statusMessage = "✓ تم تسجيل البصمة بنجاح!"
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
