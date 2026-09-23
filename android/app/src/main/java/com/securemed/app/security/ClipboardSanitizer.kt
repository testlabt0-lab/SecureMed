package com.securemed.app.security

import android.content.ClipData
import android.content.ClipDescription
import android.content.ClipboardManager
import android.content.Context
import android.os.Build
import android.os.PersistableBundle
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * Smart Clipboard Sanitizer for Healthcare Data (HIPAA / Saudi PDPL).
 *
 * 1. Tags copied clinical data with EXTRA_IS_SENSITIVE on Android 13+ to suppress
 *    clipboard previews and prevent keyboard snooping.
 * 2. Automatically wipes copied patient information from the clipboard after 30 seconds.
 * 3. Immediately clears the clipboard when the app goes into the background.
 */
object ClipboardSanitizer {

    private var autoClearJob: Job? = null
    private val scope = CoroutineScope(Dispatchers.Main.immediate)

    /**
     * Safely copies sensitive clinical text (patient ID, prescription, lab result)
     * with an automatic expiration timer.
     */
    fun copySensitive(
        context: Context,
        label: String,
        text: String,
        autoClearSeconds: Long = 30L
    ) {
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
            ?: return

        val clip = ClipData.newPlainText(label, text).apply {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                description.extras = PersistableBundle().apply {
                    putBoolean(ClipDescription.EXTRA_IS_SENSITIVE, true)
                }
            }
        }

        clipboard.setPrimaryClip(clip)

        // Cancel previous timer and start new countdown
        autoClearJob?.cancel()
        if (com.securemed.app.data.local.SecurePreferences.isClipboardAutoClearEnabled) {
            autoClearJob = scope.launch {
                delay(autoClearSeconds * 1000L)
                clearClipboard(context)
            }
        }
    }

    /**
     * Wipes the system clipboard immediately.
     */
    fun clearClipboard(context: Context, force: Boolean = false) {
        if (!force && !com.securemed.app.data.local.SecurePreferences.isClipboardAutoClearEnabled) {
            return
        }
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
            ?: return
        runCatching {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                clipboard.clearPrimaryClip()
            } else {
                clipboard.setPrimaryClip(ClipData.newPlainText("", ""))
            }
        }
    }
}
