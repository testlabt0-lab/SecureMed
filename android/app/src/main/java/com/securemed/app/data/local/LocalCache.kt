package com.securemed.app.data.local

import android.content.Context
import java.io.File

/**
 * Lightweight disk cache for offline mode.
 *
 * Successful GET responses are stored in the app's private storage. When the
 * device is offline and a request fails, the repository serves the last cached
 * copy so the app remains browsable.
 *
 * The stored bytes are sealed by [CacheCrypto] (AES-256-GCM, hardware-backed
 * key). Files keep the `.json` extension even though they are now binary: the
 * name is the migration path, letting [load] find a plaintext file written by
 * an older build, return it once, and rewrite it encrypted in place.
 *
 * Nothing here throws. A cache miss is always survivable — every entry is a
 * copy of data the server still holds — so failures degrade to "no cache"
 * instead of to an error the user sees.
 */
object LocalCache {

    private var cacheDir: File? = null

    /** Call once from SecureMedApp.onCreate(). */
    fun init(context: Context) {
        cacheDir = File(context.filesDir, "offline_cache").apply { mkdirs() }
    }

    @Synchronized
    fun save(key: String, json: String) {
        val dir = cacheDir ?: return
        try {
            // No envelope means no write. Persisting the plaintext as a
            // fallback would put patient data back on disk unprotected,
            // which is exactly what this layer exists to prevent.
            val payload = CacheCrypto.encrypt(json) ?: return
            val target = File(dir, key.sanitized() + ".json")
            val staging = File(dir, key.sanitized() + ".tmp")
            staging.writeBytes(payload)
            // Swap in one step: a half-written file would fail its GCM tag and
            // discard an entry that was still valid a moment ago.
            if (!staging.renameTo(target)) {
                target.delete()
                if (!staging.renameTo(target)) staging.delete()
            }
        } catch (_: Exception) {
            // Cache write failures must never crash the app.
        }
    }

    @Synchronized
    fun load(key: String): String? {
        return try {
            val dir = cacheDir ?: return null
            val file = File(dir, key.sanitized() + ".json")
            if (!file.exists()) return null
            val bytes = file.readBytes()
            if (CacheCrypto.looksEncrypted(bytes)) {
                CacheCrypto.decrypt(bytes) ?: run {
                    // Tag failure or a key that no longer exists (restored
                    // backup, keystore reset). The file can never be read
                    // again, so drop it rather than retry on every launch.
                    file.delete()
                    null
                }
            } else {
                // Written by a build from before cache encryption. Hand the
                // content back, then immediately seal it so the plaintext
                // stops existing on disk.
                val legacy = bytes.toString(Charsets.UTF_8)
                save(key, legacy)
                legacy
            }
        } catch (_: Exception) {
            null
        }
    }

    @Synchronized
    fun clear() {
        cacheDir?.listFiles()?.forEach { it.delete() }
    }

    /** Removes one entry — the JSON→Room migration retires files it imported. */
    @Synchronized
    fun delete(key: String) {
        try {
            val dir = cacheDir ?: return
            File(dir, key.sanitized() + ".json").delete()
            File(dir, key.sanitized() + ".tmp").delete()
        } catch (_: Exception) {
        }
    }

    private fun String.sanitized(): String = replace(Regex("[^a-zA-Z0-9_]"), "_")
}
