package com.securemed.app.ui.screens

import android.os.SystemClock
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Security
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import java.util.Locale

/** Digits in an email OTP and in a pyotp TOTP — both are six. */
private const val CODE_LENGTH = 6

/**
 * How long the server keeps `mfa_pending:{token}` alive.
 * Mirrors `timeout=300` at `backend/apps/accounts/views.py:222`.
 */
private const val CODE_LIFETIME_MS = 5 * 60 * 1000L

/**
 * Second step of a two-factor sign-in, shown in place of the login form.
 *
 * A full screen rather than a card inside [LoginScreen] because the credential
 * fields must become unreachable: a second `auth/login/` while a challenge is
 * outstanding mints a *new* `mfa_token`, which silently invalidates the code the
 * user is holding — and for the email method it also sends a second message.
 */
@Composable
fun TwoFactorScreen(
    mfaToken: String,
    method: String?,
    submitting: Boolean,
    errorMessage: String?,
    onSubmit: (String, Boolean) -> Unit,
    onExpired: () -> Unit,
    onCancel: () -> Unit
) {
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
            Text(
                text = "SecureMed",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(24.dp))
            TwoFactorCard(
                mfaToken = mfaToken,
                method = method,
                submitting = submitting,
                errorMessage = errorMessage,
                onSubmit = onSubmit,
                onExpired = onExpired,
                onCancel = onCancel
            )
        }
    }
}

/**
 * Code entry for a login the server answered with `requires_2fa`.
 *
 * The countdown is a courtesy, not the enforcement: the server is the authority
 * and answers 401 once the token is gone. Both routes end the same way — back at
 * the login form — so a client whose clock disagrees cannot strand the user on a
 * screen that can no longer succeed.
 */
@Composable
private fun TwoFactorCard(
    mfaToken: String,
    method: String?,
    submitting: Boolean,
    errorMessage: String?,
    onSubmit: (String, Boolean) -> Unit,
    onExpired: () -> Unit,
    onCancel: () -> Unit,
    modifier: Modifier = Modifier
) {
    var code by remember(mfaToken) { mutableStateOf("") }

    /**
     * `trust_device`. Off by default — trusting a device is the user's decision,
     * and the phone in someone's hand may not be their own.
     */
    var trustDevice by rememberSaveable(mfaToken) { mutableStateOf(false) }

    // Keyed on the token so a second challenge starts a second clock, and
    // saveable so a rotation does not silently restart the five minutes.
    val deadline = rememberSaveable(mfaToken) { SystemClock.elapsedRealtime() + CODE_LIFETIME_MS }
    var remainingMs by remember(mfaToken) {
        mutableLongStateOf(deadline - SystemClock.elapsedRealtime())
    }

    // elapsedRealtime, not currentTimeMillis: it keeps counting while the device
    // sleeps and cannot be moved by the user or by NTP, which is how the
    // server's own TTL behaves.
    LaunchedEffect(mfaToken) {
        while (true) {
            remainingMs = deadline - SystemClock.elapsedRealtime()
            if (remainingMs <= 0L) {
                onExpired()
                break
            }
            delay(1_000L)
        }
    }

    val byEmail = method == "email"

    Card(
        modifier = modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier.padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(
                imageVector = if (byEmail) Icons.Default.Email else Icons.Default.Security,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(40.dp)
            )

            Text(
                text = "التحقق بخطوتين",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold
            )

            Text(
                text = if (byEmail) {
                    "أرسلنا رمزاً من ٦ أرقام إلى بريدك الإلكتروني لأن الدخول جاء من جهاز جديد. " +
                        "أدخله للمتابعة."
                } else {
                    "أدخل الرمز المعروض في تطبيق المصادقة الخاص بك."
                },
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )

            OutlinedTextField(
                value = code,
                // Digits only: the IME is a suggestion, not a guarantee, and a
                // pasted "١٢٣ ٤٥٦" or a stray space would fail the server's
                // exact-string comparison for no reason the user can see.
                onValueChange = { input ->
                    code = input.filter(Char::isDigit).take(CODE_LENGTH)
                },
                label = { Text("رمز التحقق") },
                singleLine = true,
                enabled = !submitting,
                textStyle = MaterialTheme.typography.headlineSmall.copy(
                    textAlign = TextAlign.Center,
                    letterSpacing = 8.sp
                ),
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.NumberPassword,
                    imeAction = ImeAction.Done
                ),
                keyboardActions = KeyboardActions(onDone = { onSubmit(code, trustDevice) }),
                modifier = Modifier.fillMaxWidth()
            )

            Text(
                text = "ينتهي الرمز خلال ${formatRemaining(remainingMs)}",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            // Only for the mailed code. An account with an authenticator app is
            // challenged by `mfa_enabled`, which is tested before the adaptive
            // branch and never skipped — so offering to "trust" the device there
            // would promise a quieter next login that will not happen.
            if (byEmail) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .toggleable(
                            value = trustDevice,
                            enabled = !submitting,
                            role = Role.Checkbox,
                            onValueChange = { trustDevice = it }
                        ),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    // Null callback: the Row owns the toggle, so the checkbox is
                    // not a second target for screen readers to announce.
                    Checkbox(
                        checked = trustDevice,
                        onCheckedChange = null,
                        enabled = !submitting
                    )
                    Text(
                        text = "الوثوق بهذا الجهاز وعدم طلب رمز في كل مرة",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }

            errorMessage?.let {
                Text(
                    text = it,
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall,
                    textAlign = TextAlign.Center
                )
            }

            Button(
                onClick = { onSubmit(code, trustDevice) },
                enabled = !submitting && code.length == CODE_LENGTH,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp)
            ) {
                if (submitting) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = MaterialTheme.colorScheme.onPrimary,
                        strokeWidth = 2.dp
                    )
                } else {
                    Text("تأكيد الرمز")
                }
            }

            TextButton(onClick = onCancel, enabled = !submitting) {
                Text("الرجوع إلى تسجيل الدخول")
            }
        }
    }
}

/** `m:ss`, clamped at zero so a late frame never shows a negative countdown. */
private fun formatRemaining(remainingMs: Long): String {
    val totalSeconds = (remainingMs.coerceAtLeast(0L) + 999L) / 1000L
    return String.format(Locale.getDefault(), "%d:%02d", totalSeconds / 60, totalSeconds % 60)
}
