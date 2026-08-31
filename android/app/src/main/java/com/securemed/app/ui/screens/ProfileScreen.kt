package com.securemed.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Fingerprint
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.ManageAccounts
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.fragment.app.FragmentActivity
import com.securemed.app.auth.BiometricManager
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.local.SecurePreferences
import kotlinx.coroutines.launch

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
    val repository = remember { SecureMedRepository() }
    val scope = rememberCoroutineScope()

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
                                    text = if (!isBiometricAvailable) biometricManager.availabilityMessage()
                                    else if (SecurePreferences.biometricEnabled) "✓ مفعلة — استخدمها في شاشة الدخول"
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

                    // Change password (expandable)
                    ChangePasswordSection(
                        repository = repository,
                        scope = scope,
                        onStatus = { statusMessage = it }
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
                        "سيتم إنشاء مفتاح توقيع آمن داخل محفظة الجهاز (Android Keystore) " +
                        "محمي ببصمتك. لا تُغادر أي بيانات بيومترية الجهاز إطلاقاً — " +
                        "يُرسل المفتاح العام فقط للخادم."
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
                            statusMessage = "❌ نافذة غير مدعومة للمصادقة البيومترية"
                        } else if (!biometricManager.ensureSigningKey()) {
                            statusMessage = "❌ تعذر إنشاء مفتاح التوقيع الآمن"
                        } else {
                            val publicKey = biometricManager.getPublicKeyBase64()
                            if (publicKey == null) {
                                statusMessage = "❌ تعذر قراءة المفتاح العام — أعد المحاولة"
                            } else {
                                // Prove the key is usable (and biometric-gated)
                                // by signing a local enrollment challenge.
                                val enrollChallenge =
                                    "securemed-enroll-${SecurePreferences.deviceId}"
                                biometricManager.signChallenge(
                                    activity = activity,
                                    challenge = enrollChallenge,
                                    title = "تسجيل البصمة",
                                    subtitle = "SecureMed",
                                    description = "ضع إصبعك لتأمين مفتاح التسجيل",
                                    onSuccess = { _ ->
                                        scope.launch {
                                            val deviceName =
                                                "${android.os.Build.MODEL} (أندرويد)"
                                            repository.enrollBiometric(deviceName, publicKey)
                                                .onSuccess {
                                                    statusMessage =
                                                        "✓ تم تفعيل البصمة! استخدمها في شاشة الدخول"
                                                }
                                                .onFailure { error ->
                                                    statusMessage = "❌ فشل التسجيل: ${error.message}"
                                                    SecurePreferences.biometricEnabled = false
                                                }
                                        }
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
private fun ChangePasswordSection(
    repository: SecureMedRepository,
    scope: kotlinx.coroutines.CoroutineScope,
    onStatus: (String) -> Unit
) {
    var expanded by remember { mutableStateOf(false) }
    var oldPassword by remember { mutableStateOf("") }
    var newPassword by remember { mutableStateOf("") }
    var confirmPassword by remember { mutableStateOf("") }
    var showPasswords by remember { mutableStateOf(false) }
    var isSaving by remember { mutableStateOf(false) }
    var localError by remember { mutableStateOf<String?>(null) }

    Column {
        Surface(
            onClick = { expanded = !expanded },
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
                    Icons.Default.Lock,
                    null,
                    tint = MaterialTheme.colorScheme.primary
                )
                Spacer(modifier = Modifier.width(12.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        "تغيير كلمة المرور",
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.Medium
                    )
                    Text(
                        "يُنصح بتغييرها دورياً لحماية حسابك",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Text(if (expanded) "▲" else "▼")
            }
        }

        if (expanded) {
            Spacer(modifier = Modifier.height(10.dp))

            PasswordField(
                label = "كلمة المرور الحالية",
                value = oldPassword,
                onValueChange = { oldPassword = it; localError = null },
                show = showPasswords,
                onToggleShow = { showPasswords = !showPasswords }
            )
            Spacer(modifier = Modifier.height(8.dp))
            PasswordField(
                label = "كلمة المرور الجديدة",
                value = newPassword,
                onValueChange = { newPassword = it; localError = null },
                show = showPasswords,
                onToggleShow = { showPasswords = !showPasswords }
            )
            Spacer(modifier = Modifier.height(8.dp))
            PasswordField(
                label = "تأكيد كلمة المرور الجديدة",
                value = confirmPassword,
                onValueChange = { confirmPassword = it; localError = null },
                show = showPasswords,
                onToggleShow = { showPasswords = !showPasswords }
            )

            localError?.let {
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    it,
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall
                )
            }

            Spacer(modifier = Modifier.height(10.dp))
            Button(
                onClick = {
                    when {
                        oldPassword.isBlank() || newPassword.isBlank() || confirmPassword.isBlank() ->
                            localError = "يرجى إكمال جميع الحقول"
                        newPassword.length < 8 ->
                            localError = "كلمة المرور الجديدة يجب أن تكون 8 أحرف على الأقل"
                        newPassword != confirmPassword ->
                            localError = "كلمتا المرور غير متطابقتين"
                        newPassword == oldPassword ->
                            localError = "كلمة المرور الجديدة يجب أن تختلف عن الحالية"
                        else -> {
                            isSaving = true
                            localError = null
                            scope.launch {
                                repository.changePassword(oldPassword, newPassword, confirmPassword)
                                    .fold(
                                        onSuccess = {
                                            onStatus("✓ تم تغيير كلمة المرور بنجاح")
                                            oldPassword = ""
                                            newPassword = ""
                                            confirmPassword = ""
                                            expanded = false
                                        },
                                        onFailure = { error ->
                                            val msg = error.message ?: ""
                                            localError = when {
                                                msg.contains("القديمة", ignoreCase = true) ->
                                                    "كلمة المرور الحالية غير صحيحة"
                                                else -> "تعذر التغيير — تحقق من الاتصال وحاول مجدداً"
                                            }
                                        }
                                    )
                                isSaving = false
                            }
                        }
                    }
                },
                enabled = !isSaving,
                modifier = Modifier.fillMaxWidth()
            ) {
                if (isSaving) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(18.dp),
                        strokeWidth = 2.dp,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                }
                Text("حفظ كلمة المرور الجديدة")
            }
        }
    }
}

@Composable
private fun PasswordField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    show: Boolean,
    onToggleShow: () -> Unit
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = Modifier.fillMaxWidth(),
        label = { Text(label) },
        singleLine = true,
        visualTransformation = if (show) VisualTransformation.None
        else PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        trailingIcon = {
            IconButton(onClick = onToggleShow) {
                Icon(
                    if (show) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                    contentDescription = null
                )
            }
        },
        shape = RoundedCornerShape(12.dp)
    )
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
