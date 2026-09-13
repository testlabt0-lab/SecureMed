package com.securemed.app.data.local

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.securemed.app.data.local.room.SecureMedDatabase

/**
 * Secure storage for tokens and sensitive data using AndroidX Security.
 * Uses AES-256-GCM for encryption at rest.
 */
object SecurePreferences {
    private const val PREFS_NAME = "securemed_secure_prefs"
    private const val KEY_ACCESS_TOKEN = "access_token"
    private const val KEY_REFRESH_TOKEN = "refresh_token"
    private const val KEY_USER_ID = "user_id"
    private const val KEY_USER_EMAIL = "user_email"
    private const val KEY_USER_NAME = "user_name"
    private const val KEY_USER_ROLE = "user_role"
    private const val KEY_INSTALL_ID = "install_id"
    private const val KEY_BIOMETRIC_ENABLED = "biometric_enabled"
    private const val KEY_DARK_MODE = "dark_mode"
    private const val KEY_DB_PASSPHRASE = "db_passphrase"

    /** The two clocks read at the last user interaction — see [recordLastSeen]. */
    private const val KEY_LAST_SEEN_ELAPSED = "last_seen_elapsed"
    private const val KEY_LAST_SEEN_WALL = "last_seen_wall"
    private const val KEY_IDLE_TIMEOUT_MINUTES = "idle_timeout_minutes"
    private const val KEY_DEVICE_AUTHORIZED = "device_authorized"

    private lateinit var prefs: SharedPreferences

    /**
     * Cached [installId], so the value is read once per process rather than
     * decrypted on every request. Volatile because the interceptor that reads it
     * runs on OkHttp's threads while the UI may be minting it.
     */
    @Volatile
    private var cachedInstallId: String? = null

    @Synchronized
    fun init(context: Context) {
        if (::prefs.isInitialized) return
        val appContext = context.applicationContext ?: context
        try {
            createEncryptedPrefs(appContext)
        } catch (e: Exception) {
            recoverFromUnreadablePrefs(appContext, e)
            try {
                createEncryptedPrefs(appContext)
            } catch (fallbackError: Exception) {
                android.util.Log.e(
                    "SecurePreferences",
                    "Failed to create encrypted prefs, falling back to private prefs",
                    fallbackError
                )
                try {
                    prefs = appContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                } catch (spError: Exception) {
                    android.util.Log.e("SecurePreferences", "Failed to create private prefs", spError)
                }
            }
        }
    }

    private fun recoverFromUnreadablePrefs(context: Context, cause: Exception) {
        android.util.Log.e(
            "SecurePreferences",
            "Encrypted preferences unreadable (${cause.javaClass.simpleName}); rebuilding store"
        )

        try {
            context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE).edit().clear().apply()
        } catch (_: Exception) {}

        try {
            val parentDir = context.filesDir.parent
            if (parentDir != null) {
                val sharedPrefsFile = java.io.File("$parentDir/shared_prefs/$PREFS_NAME.xml")
                if (sharedPrefsFile.exists()) {
                    sharedPrefsFile.delete()
                }
            }
        } catch (_: Exception) {}

        try {
            val keyStore = java.security.KeyStore.getInstance("AndroidKeyStore")
            keyStore.load(null)
            keyStore.deleteEntry(MasterKey.DEFAULT_MASTER_KEY_ALIAS)
        } catch (_: Exception) {}

        try {
            context.deleteDatabase(SecureMedDatabase.DATABASE_NAME)
        } catch (_: Exception) {}
    }

    private fun createEncryptedPrefs(context: Context) {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

        prefs = EncryptedSharedPreferences.create(
            context,
            PREFS_NAME,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    private fun <T> safeRead(default: T, block: (SharedPreferences) -> T): T {
        if (!::prefs.isInitialized) return default
        return try {
            block(prefs)
        } catch (e: Exception) {
            android.util.Log.e("SecurePreferences", "SafeRead exception: ${e.message}", e)
            default
        }
    }

    private fun safeWrite(commit: Boolean = false, block: (SharedPreferences.Editor) -> Unit) {
        if (!::prefs.isInitialized) return
        try {
            val editor = prefs.edit()
            block(editor)
            if (commit) editor.commit() else editor.apply()
        } catch (e: Exception) {
            android.util.Log.e("SecurePreferences", "SafeWrite exception: ${e.message}", e)
        }
    }

    var accessToken: String?
        get() = safeRead(null) { it.getString(KEY_ACCESS_TOKEN, null) }
        set(value) = safeWrite { it.putString(KEY_ACCESS_TOKEN, value) }

    var refreshToken: String?
        get() = safeRead(null) { it.getString(KEY_REFRESH_TOKEN, null) }
        set(value) = safeWrite { it.putString(KEY_REFRESH_TOKEN, value) }

    var userId: String?
        get() = safeRead(null) { it.getString(KEY_USER_ID, null) }
        set(value) = safeWrite { it.putString(KEY_USER_ID, value) }

    var userEmail: String?
        get() = safeRead(null) { it.getString(KEY_USER_EMAIL, null) }
        set(value) = safeWrite { it.putString(KEY_USER_EMAIL, value) }

    var userName: String?
        get() = safeRead(null) { it.getString(KEY_USER_NAME, null) }
        set(value) = safeWrite { it.putString(KEY_USER_NAME, value) }

    var userRole: String?
        get() = safeRead(null) { it.getString(KEY_USER_ROLE, null) }
        set(value) = safeWrite { it.putString(KEY_USER_ROLE, value) }

    var biometricEnabled: Boolean
        get() = safeRead(false) { it.getBoolean(KEY_BIOMETRIC_ENABLED, false) }
        set(value) = safeWrite { it.putBoolean(KEY_BIOMETRIC_ENABLED, value) }

    var isDeviceAuthorized: Boolean
        get() = safeRead(false) { it.getBoolean(KEY_DEVICE_AUTHORIZED, false) }
        set(value) = safeWrite(commit = true) { it.putBoolean(KEY_DEVICE_AUTHORIZED, value) }

    /** Tri-state theme preference: null = follow the system setting. */
    var darkMode: Boolean?
        get() = safeRead<Boolean?>(null) { if (it.contains(KEY_DARK_MODE)) it.getBoolean(KEY_DARK_MODE, false) else null }
        set(value) {
            safeWrite {
                if (value == null) it.remove(KEY_DARK_MODE)
                else it.putBoolean(KEY_DARK_MODE, value)
            }
        }

    /**
     * Minutes of inactivity before the app locks itself. A user preference, so
     * it outlives a logout; validated on read because a value of 0 read back
     * from a corrupted file would mean "lock immediately, forever".
     */
    var idleTimeoutMinutes: Int
        get() = safeRead(5) { it.getInt(KEY_IDLE_TIMEOUT_MINUTES, 5).takeIf { m -> m > 0 } ?: 5 }
        set(value) {
            if (value > 0) safeWrite { it.putInt(KEY_IDLE_TIMEOUT_MINUTES, value) }
        }

    /** `SystemClock.elapsedRealtime()` at the last interaction, or null if none. */
    val lastSeenElapsed: Long?
        get() = safeRead<Long?>(null) { if (it.contains(KEY_LAST_SEEN_ELAPSED)) it.getLong(KEY_LAST_SEEN_ELAPSED, 0L) else null }

    /** `System.currentTimeMillis()` at the last interaction, or null if none. */
    val lastSeenWall: Long?
        get() = safeRead<Long?>(null) { if (it.contains(KEY_LAST_SEEN_WALL)) it.getLong(KEY_LAST_SEEN_WALL, 0L) else null }

    /**
     * Stores both clocks together, in one edit.
     */
    fun recordLastSeen(elapsed: Long, wall: Long) {
        safeWrite {
            it.putLong(KEY_LAST_SEEN_ELAPSED, elapsed)
                .putLong(KEY_LAST_SEEN_WALL, wall)
        }
    }

    /**
     * Forgets when the user was last seen.
     */
    fun clearLastSeen() {
        safeWrite {
            it.remove(KEY_LAST_SEEN_ELAPSED)
                .remove(KEY_LAST_SEEN_WALL)
        }
    }

    /** Drops only the session tokens — device identity and settings survive. */
    fun clearTokens() {
        safeWrite {
            it.remove(KEY_ACCESS_TOKEN)
                .remove(KEY_REFRESH_TOKEN)
        }
    }

    /**
     * Wipes the signed-in session: tokens, the cached user identity and the
     * biometric opt-in.
     */
    fun clearSession() {
        safeWrite {
            it.remove(KEY_ACCESS_TOKEN)
                .remove(KEY_REFRESH_TOKEN)
                .remove(KEY_USER_ID)
                .remove(KEY_USER_EMAIL)
                .remove(KEY_USER_NAME)
                .remove(KEY_USER_ROLE)
                .remove(KEY_BIOMETRIC_ENABLED)
                .remove(KEY_LAST_SEEN_ELAPSED)
                .remove(KEY_LAST_SEEN_WALL)
        }
    }

    /**
     * Last-resort wipe for the tamper path.
     */
    fun clearAllForWipe() {
        cachedInstallId = null
        safeWrite(commit = true) { it.clear() }
    }

    /**
     * Device identity used for every server-side binding.
     */
    val deviceId: String
        get() = installId

    /**
     * Stable per-install identifier sent as `X-Device-Fingerprint`.
     */
    val installId: String
        get() {
            cachedInstallId?.let { return it }
            return synchronized(this) {
                cachedInstallId ?: run {
                    val stored = safeRead<String?>(null) { it.getString(KEY_INSTALL_ID, null) }
                    val id = if (stored.isNullOrBlank()) {
                        val bytes = ByteArray(32)
                        java.security.SecureRandom().nextBytes(bytes)
                        val minted = bytes.joinToString("") {
                            String.format(java.util.Locale.ROOT, "%02x", it)
                        }
                        safeWrite(commit = true) { it.putString(KEY_INSTALL_ID, minted) }
                        minted
                    } else {
                        stored
                    }
                    cachedInstallId = id
                    id
                }
            }
        }

    fun isLoggedIn(): Boolean = accessToken != null && refreshToken != null

    fun getDatabasePassphrase(context: Context? = null): ByteArray {
        if (!::prefs.isInitialized && context != null) {
            init(context)
        }
        var passphrase = safeRead<String?>(null) { it.getString(KEY_DB_PASSPHRASE, null) }
        if (passphrase == null) {
            passphrase = java.util.UUID.randomUUID().toString()
            safeWrite(commit = true) { it.putString(KEY_DB_PASSPHRASE, passphrase) }
        }
        return passphrase.toByteArray()
    }
}
