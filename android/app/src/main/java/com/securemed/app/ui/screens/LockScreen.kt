package com.securemed.app.ui.screens

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.fragment.app.FragmentActivity
import com.securemed.app.auth.BiometricManager

/**
 * The idle lock, drawn over the whole app.
 *
 * An overlay rather than a navigation destination on purpose: the screens
 * underneath stay composed, so unlocking returns the user to the chart they were
 * reading and the note they had half typed. Nothing of that is visible — this
 * Surface is opaque, it swallows every pointer event before the content below can
 * see it, and `FLAG_SECURE` (set in `MainActivity`) already keeps the app out of
 * screenshots and the recents thumbnail.
 *
 * [onSignOut] is always offered. Without it a device with no fingerprint and no
 * screen lock — or one whose owner cannot use either right now — would be stuck
 * behind a prompt it can never satisfy.
 */
@Composable
fun LockScreen(
    onUnlocked: () -> Unit,
    onSignOut: () -> Unit
) {
    val context = LocalContext.current
    val biometricManager = remember { BiometricManager(context) }
    val canUnlock = remember { biometricManager.canUnlock() }

    var message by remember {
        mutableStateOf(
            if (canUnlock) null
            else "لا توجد بصمة أو قفل شاشة على هذا الجهاز، لذلك لا يمكن فتح القفل. " +
                "سجّل الخروج ثم ادخل بكلمة المرور."
        )
    }

    /**
     * A prompt is on screen. Guards against the `LaunchedEffect` raising a second
     * one over the first — `BiometricPrompt` restores its own dialog across a
     * rotation, and two live prompts leave the first one's callback orphaned.
     */
    var prompting by remember { mutableStateOf(false) }

    fun requestUnlock() {
        if (prompting) return
        val activity = context as? FragmentActivity
        if (activity == null) {
            message = "تعذر عرض نافذة التحقق"
            return
        }
        prompting = true
        biometricManager.authenticateToUnlock(
            activity = activity,
            onSuccess = {
                prompting = false
                onUnlocked()
            },
            onFailure = { error ->
                prompting = false
                // A dismissed prompt reports no error text; the lock simply stays
                // closed and the button below is how the user tries again.
                message = error ?: "التطبيق مقفل. اضغط لإعادة المحاولة."
            }
        )
    }

    // Raise the prompt as soon as the lock appears, so the common case is one
    // fingerprint touch and nothing else.
    LaunchedEffect(canUnlock) {
        if (canUnlock) requestUnlock()
    }

    // Back must not walk the navigation stack underneath a lock. Sending the app
    // to the background is what the gesture means here.
    BackHandler {
        (context as? FragmentActivity)?.moveTaskToBack(true)
    }

    Surface(
        modifier = Modifier
            .fillMaxSize()
            // Consumes pointer events in the Initial pass, before the content
            // below is offered them: an opaque Surface alone is not clickable, so
            // taps would otherwise fall straight through to the screen it covers.
            .pointerInput(Unit) {
                awaitPointerEventScope {
                    while (true) {
                        awaitPointerEvent(PointerEventPass.Initial).changes.forEach { it.consume() }
                    }
                }
            },
        color = MaterialTheme.colorScheme.background
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(32.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(
                imageVector = Icons.Default.Lock,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(56.dp)
            )
            Spacer(modifier = Modifier.height(24.dp))
            Text(
                text = "الجلسة مقفلة",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "قُفل التطبيق تلقائياً بعد فترة من عدم الاستخدام لحماية بيانات المرضى. " +
                    "جلستك ما زالت قائمة.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )

            message?.let {
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    text = it,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                    textAlign = TextAlign.Center
                )
            }

            Spacer(modifier = Modifier.height(32.dp))

            if (canUnlock) {
                Button(
                    onClick = { requestUnlock() },
                    enabled = !prompting,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(52.dp)
                ) {
                    Text("فتح القفل")
                }
                Spacer(modifier = Modifier.height(8.dp))
            }

            TextButton(onClick = onSignOut, modifier = Modifier.fillMaxWidth()) {
                Text("تسجيل الخروج")
            }
        }
    }
}
