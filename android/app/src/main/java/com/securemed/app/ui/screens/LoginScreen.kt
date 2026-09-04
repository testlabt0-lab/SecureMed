package com.securemed.app.ui.screens

import androidx.activity.ComponentActivity
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Fingerprint
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.LocalHospital
import androidx.compose.material.icons.filled.Security
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.fragment.app.FragmentActivity
import androidx.hilt.navigation.compose.hiltViewModel
import com.securemed.app.auth.BiometricManager
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.ui.AuthUiState
import com.securemed.app.ui.AuthViewModel

@Composable
fun LoginScreen(
    viewModel: AuthViewModel = hiltViewModel(),
    onLoginSuccess: () -> Unit
) {
    val context = LocalContext.current
    val uiState by viewModel.uiState.collectAsState()
    val errorMessage by viewModel.errorMessage.collectAsState()

    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var biometricMode by remember { mutableStateOf(false) }
    var showBiometricPrompt by remember { mutableStateOf(false) }

    val biometricManager = remember { BiometricManager(context) }
    val isBiometricAvailable = remember { biometricManager.isBiometricAvailable() }
    val isBiometricEnabled = remember { SecurePreferences.biometricEnabled }

    LaunchedEffect(uiState) {
        if (uiState is AuthUiState.Success) {
            onLoginSuccess()
            viewModel.resetState()
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    listOf(
                        MaterialTheme.colorScheme.primary.copy(alpha = 0.05f),
                        MaterialTheme.colorScheme.background,
                        MaterialTheme.colorScheme.secondary.copy(alpha = 0.05f)
                    )
                )
            )
            .imePadding()
            .padding(24.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Logo
            Box(
                modifier = Modifier
                    .size(80.dp)
                    .background(
                        Brush.linearGradient(
                            listOf(MaterialTheme.colorScheme.primary, MaterialTheme.colorScheme.secondary)
                        ),
                        RoundedCornerShape(20.dp)
                    ),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    Icons.Default.LocalHospital,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onPrimary,
                    modifier = Modifier.size(40.dp)
                )
            }

            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = "SecureMed",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = "منصة الرعاية الصحية الذكية الآمنة",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(modifier = Modifier.height(8.dp))
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                Icon(
                    Icons.Default.Security,
                    contentDescription = null,
                    modifier = Modifier.size(16.dp),
                    tint = MaterialTheme.colorScheme.secondary
                )
                Text(
                    text = "محمي بـ DevSecOps + HIPAA",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.secondary
                )
            }

            Spacer(modifier = Modifier.height(32.dp))

            // Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
            ) {
                Column(
                    modifier = Modifier.padding(24.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Mode toggle
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(
                                MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
                                RoundedCornerShape(12.dp)
                            )
                            .padding(4.dp)
                    ) {
                        FilterChip(
                            selected = !biometricMode,
                            onClick = { biometricMode = false },
                            label = { Text("كلمة المرور") },
                            modifier = Modifier.weight(1f)
                        )
                        FilterChip(
                            selected = biometricMode,
                            onClick = { biometricMode = true },
                            label = { Text("البصمة") },
                            modifier = Modifier.weight(1f)
                        )
                    }

                    OutlinedTextField(
                        value = email,
                        onValueChange = { email = it },
                        label = { Text("البريد الإلكتروني") },
                        leadingIcon = { Icon(Icons.Default.Email, null) },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                        modifier = Modifier.fillMaxWidth()
                    )

                    if (!biometricMode) {
                        OutlinedTextField(
                            value = password,
                            onValueChange = { password = it },
                            label = { Text("كلمة المرور") },
                            leadingIcon = { Icon(Icons.Default.Lock, null) },
                            singleLine = true,
                            visualTransformation = PasswordVisualTransformation(),
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                            modifier = Modifier.fillMaxWidth()
                        )
                    } else if (!isBiometricAvailable) {
                        Text(
                            text = "❌ البصمة غير متاحة على هذا الجهاز",
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodySmall
                        )
                    } else if (!isBiometricEnabled) {
                        Text(
                            text = "⚠️ البصمة غير مفعلة. سجل الدخول بكلمة المرور أولاً ثم فعّل البصمة من الملف الشخصي",
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodySmall
                        )
                    }

                    errorMessage?.let {
                        Text(
                            text = it,
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodySmall
                        )
                    }

                    Button(
                        onClick = {
                            if (biometricMode) {
                                showBiometricPrompt = true
                            } else {
                                viewModel.login(email, password)
                            }
                        },
                        enabled = !biometricMode || (isBiometricAvailable && isBiometricEnabled),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(52.dp),
                        colors = if (biometricMode) ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.primary,
                            contentColor = MaterialTheme.colorScheme.onPrimary
                        ) else ButtonDefaults.buttonColors()
                    ) {
                        if (uiState is AuthUiState.Loading) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                color = MaterialTheme.colorScheme.onPrimary,
                                strokeWidth = 2.dp
                            )
                        } else {
                            if (biometricMode) {
                                Icon(Icons.Default.Fingerprint, null, modifier = Modifier.size(20.dp))
                                Spacer(modifier = Modifier.width(8.dp))
                                Text("تسجيل الدخول بالبصمة")
                            } else {
                                Text("تسجيل الدخول")
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))
            Text(
                text = "© 2026 SecureMed - مشروع تصميم وهندسة البرمجيات الآمنة",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f)
            )
        }
    }

    // Biometric Prompt
    if (showBiometricPrompt) {
        LaunchedEffect(Unit) {
            val activity = context as? FragmentActivity
            activity?.let {
                val cryptoObject = com.securemed.app.security.BiometricHelper.getCryptoObject()
                biometricManager.authenticate(
                    activity = it,
                    title = "المصادقة بالبصمة",
                    subtitle = "استخدم بصمتك للدخول إلى SecureMed",
                    description = "SecureMed يتطلب المصادقة البيومترية للوصول للبيانات الحساسة",
                    cryptoObject = cryptoObject,
                    onSuccess = { result ->
                        val cipher = result.cryptoObject?.cipher
                        val template = if (cipher != null) {
                            // Encrypt a challenge (e.g., email + timestamp) to prove key ownership
                            com.securemed.app.security.BiometricHelper.encryptChallenge(cipher, "securemed-challenge-$email")
                        } else {
                            // Fallback if CryptoObject failed but auth succeeded
                            "android-bio-$email-${System.currentTimeMillis()}-${(0..9999).random()}"
                        }
                        viewModel.biometricLogin(email, template)
                        showBiometricPrompt = false
                    },
                    onError = { error ->
                        viewModel.resetState()
                        showBiometricPrompt = false
                    },
                    onCancel = {
                        showBiometricPrompt = false
                    }
                )
            }
        }
    }
}
