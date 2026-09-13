package com.securemed.app.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.HourglassTop
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Mail
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
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

    // Navigate on a positive signal (DeviceAuthorized).
    LaunchedEffect(uiState) {
        if (uiState is AuthUiState.DeviceAuthorized) {
            onDeviceAuthorized()
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
        contentAlignment = Alignment.Center
    ) {
        when (val state = uiState) {
            is AuthUiState.CheckingDevice, AuthUiState.Loading -> {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.padding(24.dp)
                ) {
                    CircularProgressIndicator(strokeWidth = 3.dp)
                    Spacer(modifier = Modifier.height(20.dp))
                    Text(
                        text = "جاري التحقق الأمني من الجهاز والشبكة...",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "فحص تصريح الوصول الصفري (ZTNA)",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            is AuthUiState.ZtnaRequired -> {
                ZtnaRequiredView(
                    state = state,
                    onSendRequest = {
                        viewModel.sendZtnaAccessRequest(state.fingerprint, state.macAddress)
                    },
                    onRecheck = {
                        viewModel.checkDeviceAuthorization(state.fingerprint, state.macAddress)
                    }
                )
            }

            is AuthUiState.ZtnaSending -> {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.padding(32.dp)
                ) {
                    CircularProgressIndicator(strokeWidth = 3.dp)
                    Spacer(modifier = Modifier.height(20.dp))
                    Text(
                        text = "جاري إرسال بيانات الجهاز إلى تيليجرام المدير...",
                        style = MaterialTheme.typography.titleMedium,
                        textAlign = TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "يرجى الانتظار بضع ثوانٍ...",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            is AuthUiState.ZtnaPending -> {
                ZtnaPendingView(
                    state = state,
                    onRecheck = {
                        viewModel.checkDeviceAuthorization(state.fingerprint)
                    },
                    onResend = {
                        val mac = SecurityUtils.getMacAddress(context)
                        viewModel.sendZtnaAccessRequest(state.fingerprint, mac)
                    }
                )
            }

            is AuthUiState.ZtnaRejected -> {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier
                        .padding(32.dp)
                        .verticalScroll(rememberScrollState())
                ) {
                    Icon(
                        imageVector = Icons.Default.Warning,
                        contentDescription = "Access Rejected",
                        modifier = Modifier.size(64.dp),
                        tint = MaterialTheme.colorScheme.error
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = "تم رفض طلب الوصول",
                        style = MaterialTheme.typography.headlineSmall,
                        color = MaterialTheme.colorScheme.error,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = state.message,
                        style = MaterialTheme.typography.bodyMedium,
                        textAlign = TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(24.dp))
                    Button(
                        onClick = {
                            val fingerprint = SecurityUtils.getDeviceFingerprint(context)
                            val macAddress = SecurityUtils.getMacAddress(context)
                            viewModel.checkDeviceAuthorization(fingerprint, macAddress)
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Default.Refresh, contentDescription = null)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("إعادة المحاولة")
                    }
                }
            }

            is AuthUiState.DeviceUnauthorized -> {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier
                        .padding(32.dp)
                        .verticalScroll(rememberScrollState())
                ) {
                    Icon(
                        imageVector = Icons.Default.Warning,
                        contentDescription = "Device Unauthorized",
                        modifier = Modifier.size(64.dp),
                        tint = MaterialTheme.colorScheme.error
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = "جهاز أو شبكة غير مصرح بها",
                        style = MaterialTheme.typography.headlineSmall,
                        color = MaterialTheme.colorScheme.error,
                        fontWeight = FontWeight.Bold
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
                // Idle / DeviceAuthorized. Transitioning to next screen.
            }
        }
    }
}

@Composable
private fun ZtnaRequiredView(
    state: AuthUiState.ZtnaRequired,
    onSendRequest: () -> Unit,
    onRecheck: () -> Unit
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp)
    ) {
        Spacer(modifier = Modifier.height(16.dp))

        Box(
            modifier = Modifier
                .size(72.dp)
                .clip(RoundedCornerShape(20.dp))
                .background(MaterialTheme.colorScheme.primaryContainer),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = Icons.Default.Security,
                contentDescription = null,
                modifier = Modifier.size(40.dp),
                tint = MaterialTheme.colorScheme.primary
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "تصريح وصول أمني (ZTNA)",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onBackground
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = state.message ?: "يتطلب النظام التحقق من الجهاز وموافقة المدير عبر تيليجرام قبل السماح بالدخول.",
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(24.dp))

        // Device information card
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f)
            )
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "معلومات وهوية الجهاز والاتصال:",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )

                Spacer(modifier = Modifier.height(12.dp))

                DeviceInfoRow(
                    label = "🌐 عنوان IP المحلي",
                    value = state.localIp ?: "يحدده الخادم تلقائياً"
                )

                DeviceInfoRow(
                    label = "📟 عنوان MAC",
                    value = state.macAddress
                )

                DeviceInfoRow(
                    label = "📱 طراز الجهاز",
                    value = state.deviceModel
                )

                DeviceInfoRow(
                    label = "⚙️ نظام التشغيل",
                    value = state.osInfo
                )

                DeviceInfoRow(
                    label = "🔑 بصمة الجهاز",
                    value = state.fingerprint.take(16) + "...",
                    isCode = true
                )
            }
        }

        Spacer(modifier = Modifier.height(28.dp))

        Button(
            onClick = onSendRequest,
            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp),
            shape = RoundedCornerShape(12.dp)
        ) {
            Icon(Icons.AutoMirrored.Filled.Send, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "طلب تصريح من المدير (إرسال لتيليجرام)",
                fontWeight = FontWeight.Bold,
                fontSize = 15.sp
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        OutlinedButton(
            onClick = onRecheck,
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp),
            shape = RoundedCornerShape(12.dp)
        ) {
            Icon(Icons.Default.Refresh, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("فحص حالة التصريح")
        }

        Spacer(modifier = Modifier.height(16.dp))
    }
}

@Composable
private fun ZtnaPendingView(
    state: AuthUiState.ZtnaPending,
    onRecheck: () -> Unit,
    onResend: () -> Unit
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp)
    ) {
        Spacer(modifier = Modifier.height(24.dp))

        Box(
            modifier = Modifier
                .size(72.dp)
                .clip(RoundedCornerShape(20.dp))
                .background(MaterialTheme.colorScheme.tertiaryContainer),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = Icons.Default.HourglassTop,
                contentDescription = null,
                modifier = Modifier.size(40.dp),
                tint = MaterialTheme.colorScheme.tertiary
            )
        }

        Spacer(modifier = Modifier.height(20.dp))

        Text(
            text = "بانتظار موافقة المدير",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onBackground
        )

        Spacer(modifier = Modifier.height(12.dp))

        Text(
            text = state.message,
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(24.dp))

        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
            )
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.Center,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        strokeWidth = 2.5.dp,
                        color = MaterialTheme.colorScheme.primary
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(
                        text = "جاري الاستماع لقرار المدير لحظياً...",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.primary
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                Text(
                    text = "فور قيام المدير بالنقر على زر [✅ السماح بالدخول] في تطبيق تيليجرام، ستفتح لك شاشة تسجيل الدخول تلقائياً.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                    lineHeight = 20.sp
                )
            }
        }

        Spacer(modifier = Modifier.height(32.dp))

        Button(
            onClick = onRecheck,
            modifier = Modifier
                .fillMaxWidth()
                .height(50.dp),
            shape = RoundedCornerShape(12.dp)
        ) {
            Icon(Icons.Default.Refresh, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("فحص الحالة الآن")
        }

        Spacer(modifier = Modifier.height(12.dp))

        OutlinedButton(
            onClick = onResend,
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp),
            shape = RoundedCornerShape(12.dp)
        ) {
            Icon(Icons.AutoMirrored.Filled.Send, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("إعادة إرسال الطلب لتيليجرام")
        }
    }
}

@Composable
private fun DeviceInfoRow(
    label: String,
    value: String,
    isCode: Boolean = false
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(
            text = value,
            style = if (isCode) {
                MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace)
            } else {
                MaterialTheme.typography.bodySmall
            },
            fontWeight = FontWeight.Medium,
            color = MaterialTheme.colorScheme.onSurface
        )
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

