package com.securemed.app.data.local

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

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
    private const val KEY_DEVICE_ID = "device_id"
    private const val KEY_BIOMETRIC_ENABLED = "biometric_enabled"
    private const val KEY_DARK_MODE = "dark_mode"
    private const val KEY_DB_PASSPHRASE = "db_passphrase"

    private lateinit var prefs: EncryptedSharedPreferences

    fun init(context: Context) {
        try {
            createEncryptedPrefs(context)
        } catch (e: Exception) {
            // Android KeyStore / SecurityException occasionally happens on some devices
            // If the keys are corrupted, delete the preferences file and try again
            android.util.Log.e("SecurePreferences", "Error creating EncryptedSharedPreferences, clearing and retrying: ${e.message}")
            context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE).edit().clear().apply()
            
            // Delete the file manually for safety
            val sharedPrefsFile = java.io.File(context.filesDir.parent + "/shared_prefs/" + PREFS_NAME + ".xml")
            if (sharedPrefsFile.exists()) {
                sharedPrefsFile.delete()
            }
            
            // Delete the master key alias from Keystore
            try {
                val keyStore = java.security.KeyStore.getInstance("AndroidKeyStore")
                keyStore.load(null)
                keyStore.deleteEntry(MasterKey.DEFAULT_MASTER_KEY_ALIAS)
            } catch (ex: Exception) {
                // Ignore errors while cleaning Keystore
            }
            
            createEncryptedPrefs(context)
        }
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
        ) as EncryptedSharedPreferences
    }

    var accessToken: String?
        get() = prefs.getString(KEY_ACCESS_TOKEN, null)
        set(value) = prefs.edit().putString(KEY_ACCESS_TOKEN, value).apply()

    var refreshToken: String?
        get() = prefs.getString(KEY_REFRESH_TOKEN, null)
        set(value) = prefs.edit().putString(KEY_REFRESH_TOKEN, value).apply()

    var userId: String?
        get() = prefs.getString(KEY_USER_ID, null)
        set(value) = prefs.edit().putString(KEY_USER_ID, value).apply()

    var userEmail: String?
        get() = prefs.getString(KEY_USER_EMAIL, null)
        set(value) = prefs.edit().putString(KEY_USER_EMAIL, value).apply()

    var userName: String?
        get() = prefs.getString(KEY_USER_NAME, null)
        set(value) = prefs.edit().putString(KEY_USER_NAME, value).apply()

    var userRole: String?
        get() = prefs.getString(KEY_USER_ROLE, null)
        set(value) = prefs.edit().putString(KEY_USER_ROLE, value).apply()

    var biometricEnabled: Boolean
        get() = prefs.getBoolean(KEY_BIOMETRIC_ENABLED, false)
        set(value) = prefs.edit().putBoolean(KEY_BIOMETRIC_ENABLED, value).apply()

    /** Tri-state theme preference: null = follow the system setting. */
    var darkMode: Boolean?
        get() = if (prefs.contains(KEY_DARK_MODE)) prefs.getBoolean(KEY_DARK_MODE, false) else null
        set(value) {
            if (value == null) prefs.edit().remove(KEY_DARK_MODE).apply()
            else prefs.edit().putBoolean(KEY_DARK_MODE, value).apply()
        }

    /** Drops only the session tokens — device identity and settings survive. */
    fun clearTokens() {
        prefs.edit()
            .remove(KEY_ACCESS_TOKEN)
            .remove(KEY_REFRESH_TOKEN)
            .apply()
    }

    val deviceId: String
        get() {
            var id = prefs.getString(KEY_DEVICE_ID, null)
            if (id == null) {
                id = "android-${System.currentTimeMillis()}-${(0..9999).random()}"
                prefs.edit().putString(KEY_DEVICE_ID, id).apply()
            }
            return id
        }

    fun clear() {
        prefs.edit().clear().apply()
    }

    fun isLoggedIn(): Boolean = accessToken != null && refreshToken != null

    fun getDatabasePassphrase(): ByteArray {
        var passphrase = prefs.getString(KEY_DB_PASSPHRASE, null)
        if (passphrase == null) {
            passphrase = java.util.UUID.randomUUID().toString()
            prefs.edit().putString(KEY_DB_PASSPHRASE, passphrase).apply()
        }
        return passphrase.toByteArray()
    }
}
