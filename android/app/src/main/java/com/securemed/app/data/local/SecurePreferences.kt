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
    private const val KEY_LAST_EMAIL = "last_email"

    private lateinit var prefs: EncryptedSharedPreferences

    fun init(context: Context) {
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

    var darkMode: Boolean
        get() = prefs.getBoolean(KEY_DARK_MODE, false)
        set(value) = prefs.edit().putBoolean(KEY_DARK_MODE, value).apply()

    /** Last successfully logged-in email — prefills the biometric login tab. */
    var lastEmail: String?
        get() = prefs.getString(KEY_LAST_EMAIL, null)
        set(value) = prefs.edit().putString(KEY_LAST_EMAIL, value).apply()

    val deviceId: String
        get() {
            var id = prefs.getString(KEY_DEVICE_ID, null)
            if (id == null) {
                id = "android-${System.currentTimeMillis()}-${(0..9999).random()}"
                prefs.edit().putString(KEY_DEVICE_ID, id).apply()
            }
            return id
        }

    /**
     * End the session WITHOUT wiping device-bound data.
     *
     * deviceId must survive logout: it identifies the biometric enrollment
     * on the server. Wiping it used to break fingerprint login after the
     * first logout (device no longer recognized).
     */
    fun clearSession() {
        val keepDeviceId = prefs.getString(KEY_DEVICE_ID, null)
        val keepBiometric = prefs.getBoolean(KEY_BIOMETRIC_ENABLED, false)
        val keepEmail = prefs.getString(KEY_LAST_EMAIL, null)
        prefs.edit().clear().apply()
        prefs.edit()
            .putString(KEY_DEVICE_ID, keepDeviceId)
            .putBoolean(KEY_BIOMETRIC_ENABLED, keepBiometric)
            .putString(KEY_LAST_EMAIL, keepEmail)
            .apply()
    }

    fun clear() {
        prefs.edit().clear().apply()
    }

    fun isLoggedIn(): Boolean = accessToken != null && refreshToken != null
}
