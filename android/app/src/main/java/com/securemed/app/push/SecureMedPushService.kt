package com.securemed.app.push

import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.reminders.NotificationHelper
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * FCM push receiver.
 *
 * Registration is self-guarding: if the build was made without
 * google-services.json (FirebaseInitProvider never initializes),
 * FirebaseMessaging.getInstance() throws IllegalStateException and every entry
 * point here turns into a silent no-op — in-app and local notifications keep
 * working exactly as before, and nothing logs spam or crashes.
 *
 * Tokens are pushed to the backend (`notifications/push/register/`) whenever
 * Firebase rotates them, bound to the currently signed-in account. A token
 * arriving before login is dropped: the backend would otherwise hold a push
 * channel for an account that has not authenticated this device.
 */
@AndroidEntryPoint
class SecureMedPushService : FirebaseMessagingService() {

    @Inject lateinit var repository: SecureMedRepository

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onNewToken(token: String) {
        val sessionOpen = SecurePreferences.isLoggedIn()
        if (!sessionOpen) return

        scope.launch {
            try {
                repository.registerPushToken(token)
            } catch (_: Exception) {
                // Best-effort: the next token rotation or a manual retry
                // registers it. Push must never be on the critical path.
            }
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val title = message.notification?.title
            ?: message.data["title"]
            ?: "SecureMed"
        val body = message.notification?.body
            ?: message.data["message"]
            ?: ""

        if (title.isBlank() && body.isBlank()) return

        // Rendered through the same helper as medication reminders: one
        // notification style, one private lock-screen policy.
        try {
            NotificationHelper.showNotification(applicationContext, title, body)
        } catch (_: Exception) {
        }
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }
}
