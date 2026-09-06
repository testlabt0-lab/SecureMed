package com.securemed.app.ui.screens

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
import androidx.compose.runtime.saveable.rememberSaveable
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
import com.securemed.app.security.BiometricHelper
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

    val biometricManager = remember { BiometricManager(context) }
    val isBiometricAvailable = remember { biometricManager.isBiometricAvailable() }

    /**
     * The real precondition for a biometric login is a signing key in this
     * device's Keystore, not the `biometricEnabled` session flag this screen used
     * to read: logout clears that flag while the key and the server-side
     * enrollment both survive, so the button was disabled exactly when it was
     * needed. It is mutable because a fingerprint added since enrollment
     * invalidates the key, and we only find that out when we try to use it.
     */
    var hasBiometricKey by remember { mutableStateOf(BiometricHelper.hasKey()) }

    /**
     * The challenge a prompt has already been raised for.
     *
     * `rememberSaveable`, because the ViewModel keeps [AuthUiState.AwaitingBiometric]
     * across a rotation while the composition is rebuilt: without this the
     * `LaunchedEffect` below would fire a second prompt on top of the one
     * `BiometricPrompt` restores by itself, and the first CryptoObject — the only
     * one that can sign — would be thrown away.
     */
    var promptedChallengeId by rememberSaveable { mutableStateOf<String?>(null) }

    LaunchedEffect(uiState) {
        if (uiState is AuthUiState.Success) {
            onLoginSuccess()
            viewModel.resetState()
        }
    }

    // A pending second factor takes over the screen. Leaving the credential
    // fields reachable would invite a second login attempt while a challenge is
    // outstanding, and that mints a new mfa_token — silently invalidating the
    // code the user is already holding. `email`/`password` are remembered above
    // this branch, so cancelling or timing out comes back to a filled form.
    val twoFactor = uiState as? AuthUiState.AwaitingTwoFactor
    if (twoFactor != null) {
        TwoFactorScreen(
            mfaToken = twoFactor.mfaToken,
            method = twoFactor.method,
            submitting = twoFactor.submitting,
            errorMessage = errorMessage,
            // Explicit lambda rather than a method reference: the ViewModel
            // function's second parameter has a default, so a reference could
            // bind the one-argument adaptation and silently drop `trust_device`.
            onSubmit = { code, trust -> viewModel.submitTwoFactorCode(code, trust) },
            onExpired = { viewModel.expireTwoFactor() },
            onCancel = { viewModel.cancelTwoFactor() }
        )
        return
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
                    } else if (!hasBiometricKey) {
                        Text(
                            text = "⚠️ لا توجد بصمة مسجلة على هذا الجهاز. سجل الدخول بكلمة المرور ثم فعّل البصمة من الملف الشخصي",
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
                                // Fetch the challenge first: the prompt has to
                                // sign something the server chose, so there is
                                // nothing to unlock until it arrives.
                                if (email.isBlank()) {
                                    viewModel.failBiometric("أدخل البريد الإلكتروني أولاً")
                                } else {
                                    viewModel.startBiometricLogin(email)
                                }
                            } else {
                                viewModel.login(email, password)
                            }
                        },
                        enabled = !biometricMode || (isBiometricAvailable && hasBiometricKey),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(52.dp),
                        colors = if (biometricMode) ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.primary,
                            contentColor = MaterialTheme.colorScheme.onPrimary
                        ) else ButtonDefaults.buttonColors()
                    ) {
                        if (uiState is AuthUiState.Loading ||
                            uiState is AuthUiState.AwaitingBiometric
                        ) {
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
    //
    // Driven by AwaitingBiometric, so the order is fixed by construction:
    // challenge from the server, then the prompt, then a signature over that
    // challenge. The previous version ran the prompt first and encrypted a
    // locally built string ("securemed-challenge-$email"), then fell back to a
    // random string when the CryptoObject was missing — which meant a failure to
    // unlock the key still produced a "credential" and still attempted a login.
    val awaiting = uiState as? AuthUiState.AwaitingBiometric
    if (awaiting != null) {
        LaunchedEffect(awaiting.challenge.challengeId) {
            if (promptedChallengeId == awaiting.challenge.challengeId) {
                // A prompt for this challenge is already on screen.
                return@LaunchedEffect
            }
            promptedChallengeId = awaiting.challenge.challengeId
            val activity = context as? FragmentActivity
            if (activity == null) {
                viewModel.failBiometric("تعذر عرض نافذة البصمة")
                return@LaunchedEffect
            }
            when (val unlock = BiometricHelper.unlockForSigning()) {
                is BiometricHelper.Unlock.Ready -> biometricManager.authenticate(
                    activity = activity,
                    title = "المصادقة بالبصمة",
                    subtitle = "استخدم بصمتك للدخول إلى SecureMed",
                    description = "SecureMed يتطلب المصادقة البيومترية للوصول للبيانات الحساسة",
                    cryptoObject = unlock.cryptoObject,
                    onSuccess = { result ->
                        // The Signature the Keystore released; only this object
                        // can sign, and only once.
                        val signer = result.cryptoObject?.signature
                        if (signer == null) {
                            viewModel.failBiometric("لم يوفر النظام مفتاح التوقيع")
                        } else {
                            try {
                                viewModel.completeBiometricLogin(
                                    awaiting.challenge.challengeId,
                                    BiometricHelper.signChallenge(
                                        signer, awaiting.challenge.challenge
                                    )
                                )
                            } catch (e: Exception) {
                                viewModel.failBiometric(
                                    e.message ?: "تعذر توقيع تحدي المصادقة"
                                )
                            }
                        }
                    },
                    onError = { error -> viewModel.failBiometric(error) },
                    onCancel = { viewModel.resetState() }
                )

                BiometricHelper.Unlock.NotEnrolled -> {
                    hasBiometricKey = false
                    viewModel.failBiometric(
                        "لا توجد بصمة مسجلة على هذا الجهاز. سجل الدخول بكلمة المرور ثم فعّلها من الملف الشخصي"
                    )
                }

                BiometricHelper.Unlock.Invalidated -> {
                    // A fingerprint was added or removed after enrollment, so the
                    // Keystore destroyed the key. This is the protection working:
                    // a finger added to an unlocked phone must not inherit the
                    // owner's enrollment.
                    hasBiometricKey = false
                    viewModel.failBiometric(
                        "تغيّرت بصمات الجهاز، لذلك أُلغي المفتاح. سجل الدخول بكلمة المرور وفعّل البصمة من جديد"
                    )
                }

                is BiometricHelper.Unlock.Failed ->
                    viewModel.failBiometric(unlock.message)
            }
        }
    }
}
