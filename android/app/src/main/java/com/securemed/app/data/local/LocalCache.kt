package com.securemed.app.data.local

import android.content.Context
import java.io.File

/**
 * Lightweight disk cache for offline mode.
 *
 * Successful GET responses are stored as JSON files in the app's private
 * storage. When the device is offline and a request fails, the repository
 * serves the last cached copy so the app remains browsable.
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
            File(dir, key.sanitized() + ".json").writeText(json)
        } catch (_: Exception) {
            // Cache write failures must never crash the app.
        }
    }

    @Synchronized
    fun load(key: String): String? {
        return try {
            val dir = cacheDir ?: return null
            val file = File(dir, key.sanitized() + ".json")
            if (file.exists()) file.readText() else null
        } catch (_: Exception) {
            null
        }
    }

    @Synchronized
    fun clear() {
        cacheDir?.listFiles()?.forEach { it.delete() }
    }

    private fun String.sanitized(): String = replace(Regex("[^a-zA-Z0-9_]"), "_")
}
