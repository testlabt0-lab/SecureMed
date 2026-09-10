package com.securemed.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.HourglassTop
import androidx.compose.material.icons.filled.Mail
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.securemed.app.security.SecurityUtils
import com.securemed.app.ui.AuthUiState
import com.securemed.app.ui.AuthViewModel

@Composable
fun DeviceCheckScreen(
    viewModel: AuthViewModel = hiltViewModel(),
    onDeviceAuthorized: () -> Unit
) {
    val context = LocalContext.current
    val uiState by viewModel.uiState.collectAsState()

    // Trigger the pre-flight check exactly once when the screen appears.
    LaunchedEffect(Unit) {
        val fingerprint = SecurityUtils.getDeviceFingerprint(context)
        val macAddress = SecurityUtils.getMacAddress(context)
        viewModel.checkDeviceAuthorization(fingerprint, macAddress)
    }

    // Navigate on a *positive* signal (DeviceAuthorized). The previous
    // implementation watched for Idle, but Idle is also the initial state
    // before any check has run — so it triggered navigation on the very
    // first composition, before the network response had come back, and
    // the device check was effectively bypassed.
    LaunchedEffect(uiState) {
        if (uiState is AuthUiState.DeviceAuthorized) {
            onDeviceAuthorized()
        }
    }

    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        when (val state = uiState) {
            is AuthUiState.CheckingDevice, AuthUiState.Loading -> {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    CircularProgressIndicator()
                    Spacer(modifier = Modifier.height(16.dp))
                    Text("جاري التحقق من الجهاز...", style = MaterialTheme.typography.titleMedium)
                }
            }
            is AuthUiState.DeviceUnauthorized -> {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.padding(32.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Warning,
                        contentDescription = "Device Unauthorized",
                        modifier = Modifier.size(64.dp),
                        tint = MaterialTheme.colorScheme.error
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = "جهاز غير مصرح",
                        style = MaterialTheme.typography.headlineMedium,
                        color = MaterialTheme.colorScheme.error
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = state.message,
                        style = MaterialTheme.typography.bodyLarge,
                        textAlign = TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(32.dp))
                    Button(onClick = {
                        val fingerprint = SecurityUtils.getDeviceFingerprint(context)
                        val macAddress = SecurityUtils.getMacAddress(context)
                        viewModel.checkDeviceAuthorization(fingerprint, macAddress)
                    }) {
                        Text("إعادة المحاولة")
                    }
                }
            }
            is AuthUiState.DevicePending -> {
                // طلب التفعيل في طابور الإدارة: شاشة انتظار مع إعادة فحص،
                // لا شاشة خطأ — الرسالة الجديدة من الإدارة تصل كإشعار داخل
                // التطبيق عند قرار الإدارة.
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.padding(32.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.HourglassTop,
                        contentDescription = "Pending approval",
                        modifier = Modifier.size(64.dp),
                        tint = MaterialTheme.colorScheme.tertiary
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = "بانتظار موافقة الإدارة",
                        style = MaterialTheme.typography.headlineMedium,
                        color = MaterialTheme.colorScheme.tertiary
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = state.message,
                        style = MaterialTheme.typography.bodyLarge,
                        textAlign = TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "ستصلك رسالة داخل التطبيق عند اتخاذ القرار.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(32.dp))
                    Button(onClick = {
                        val fingerprint = SecurityUtils.getDeviceFingerprint(context)
                        val macAddress = SecurityUtils.getMacAddress(context)
                        viewModel.checkDeviceAuthorization(fingerprint, macAddress)
                    }) {
                        Text("فحص الحالة مرة أخرى")
                    }
                }
            }
            is AuthUiState.DeviceUnknown -> {
                DeviceRegistrationForm(
                    initialMessage = state.message,
                    onSubmit = { email ->
                        val fingerprint = SecurityUtils.getDeviceFingerprint(context)
                        val macAddress = SecurityUtils.getMacAddress(context)
                        viewModel.checkDeviceAuthorization(fingerprint, macAddress, email)
                    }
                )
            }
            else -> {
                // Idle / DeviceAuthorized. The Authorized branch is handled
                // by the LaunchedEffect above; this branch only exists to
                // cover the moment after the check returns authorized and
                // before navigation finishes.
            }
        }
    }
}

@Composable
private fun DeviceRegistrationForm(
    initialMessage: String,
    onSubmit: (String) -> Unit
) {
    var email by rememberSaveable { mutableStateOf("") }

    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .fillMaxWidth()
            .padding(32.dp)
    ) {
        Icon(
            imageVector = Icons.Default.Security,
            contentDescription = null,
            modifier = Modifier.size(56.dp),
            tint = MaterialTheme.colorScheme.primary
        )
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "تسجيل جهاز جديد",
            style = MaterialTheme.typography.headlineSmall
        )
        Spacer(modifier = Modifier.height(12.dp))
        Text(
            text = initialMessage,
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center
        )
        Spacer(modifier = Modifier.height(24.dp))
        OutlinedTextField(
            value = email,
            onValueChange = { email = it.trim() },
            label = { Text("البريد الإلكتروني") },
            singleLine = true,
            leadingIcon = { Icon(Icons.Default.Mail, null) },
            keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(
                keyboardType = KeyboardType.Email
            ),
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(modifier = Modifier.height(16.dp))
        Button(
            onClick = { onSubmit(email) },
            enabled = email.contains('@') && email.contains('.'),
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("إرسال طلب التفعيل")
        }
    }
}
