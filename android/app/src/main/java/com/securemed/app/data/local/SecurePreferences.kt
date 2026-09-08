package com.securemed.app.data.local

import android.content.Context
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
    private const val KEY_DEVICE_ID = "device_id"
    private const val KEY_INSTALL_ID = "install_id"
    private const val KEY_BIOMETRIC_ENABLED = "biometric_enabled"
    private const val KEY_DARK_MODE = "dark_mode"
    private const val KEY_DB_PASSPHRASE = "db_passphrase"

    /** The two clocks read at the last user interaction — see [recordLastSeen]. */
    private const val KEY_LAST_SEEN_ELAPSED = "last_seen_elapsed"
    private const val KEY_LAST_SEEN_WALL = "last_seen_wall"
    private const val KEY_IDLE_TIMEOUT_MINUTES = "idle_timeout_minutes"

    private lateinit var prefs: EncryptedSharedPreferences

    /**
     * Cached [installId], so the value is read once per process rather than
     * decrypted on every request. Volatile because the interceptor that reads it
     * runs on OkHttp's threads while the UI may be minting it.
     */
    @Volatile
    private var cachedInstallId: String? = null

    fun init(context: Context) {
        try {
            createEncryptedPrefs(context)
        } catch (e: Exception) {
            recoverFromUnreadablePrefs(context, e)
            createEncryptedPrefs(context)
        }
    }

    /**
     * Rebuilds the store when [EncryptedSharedPreferences] cannot be opened at
     * all.
     *
     * This happens for real rather than theoretically: a device-to-device restore
     * brings the encrypted file without the hardware key that sealed it, and a
     * Keystore reset leaves the same mismatch. The file is undecryptable either
     * way, so it and the master key are dropped and everything is minted afresh —
     * an app that only rethrew here would never start again.
     *
     * The database is deleted with them, and that is the part this recovery was
     * missing. [KEY_DB_PASSPHRASE] lives in the file being deleted and is the only
     * key to the SQLCipher database, but the database file itself survives — so
     * the rebuilt store minted a *new* passphrase for a file it could not open,
     * and every Room access afterwards threw "file is not a database", on every
     * launch, with reinstalling the app the only way out. Deleting it costs
     * nothing that cannot be refetched: every row is a copy of data the server
     * still holds (see [SecureMedDatabase]).
     *
     * The offline cache is deliberately left alone. It is sealed by
     * `CacheCrypto`'s own Keystore alias rather than by this master key, so it may
     * well still be readable — and unlike Room it holds the only copy of the
     * medication plans and dose logs. Entries it can no longer decrypt are dropped
     * one at a time as they are read.
     *
     * What the user notices: they are signed out, and the backend sees an unknown
     * device — [KEY_INSTALL_ID] and [KEY_DEVICE_ID] went with the file — so
     * adaptive MFA challenges the next login and biometric login has to be
     * enrolled again.
     */
    private fun recoverFromUnreadablePrefs(context: Context, cause: Exception) {
        // The exception type, not its message: this is the one code path that
        // handles key material, and the log is readable over adb.
        android.util.Log.e(
            "SecurePreferences",
            "Encrypted preferences unreadable (${cause.javaClass.simpleName}); rebuilding store"
        )

        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE).edit().clear().apply()

        // clear() only empties the map; the file has to go too, or the next
        // EncryptedSharedPreferences.create reads the same undecryptable bytes.
        val parentDir = context.filesDir.parent
        if (parentDir != null) {
            val sharedPrefsFile = java.io.File("$parentDir/shared_prefs/$PREFS_NAME.xml")
            if (sharedPrefsFile.exists()) {
                sharedPrefsFile.delete()
            }
        }

        try {
            val keyStore = java.security.KeyStore.getInstance("AndroidKeyStore")
            keyStore.load(null)
            keyStore.deleteEntry(MasterKey.DEFAULT_MASTER_KEY_ALIAS)
        } catch (_: Exception) {
            // A key that refuses to be deleted is not a reason to stop: the
            // MasterKey.Builder call that follows replaces the alias regardless.
        }

        try {
            // deleteDatabase rather than File.delete: it takes the -wal, -shm and
            // -journal companions with it, and a stale WAL left beside a fresh
            // database is unopenable in exactly the same way. Safe to call here
            // because this runs first in Application.onCreate, before Hilt has
            // built the database and before any DAO exists.
            context.deleteDatabase(SecureMedDatabase.DATABASE_NAME)
        } catch (_: Exception) {
            // Losing the race with an open handle is the only way this fails, and
            // the app still starts; Room reports it at the first query.
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

    /**
     * Minutes of inactivity before the app locks itself. A user preference, so
     * it outlives a logout; validated on read because a value of 0 read back
     * from a corrupted file would mean "lock immediately, forever".
     */
    var idleTimeoutMinutes: Int
        get() = prefs.getInt(KEY_IDLE_TIMEOUT_MINUTES, 5).takeIf { it > 0 } ?: 5
        set(value) {
            if (value > 0) prefs.edit().putInt(KEY_IDLE_TIMEOUT_MINUTES, value).apply()
        }

    /** `SystemClock.elapsedRealtime()` at the last interaction, or null if none. */
    val lastSeenElapsed: Long?
        get() = if (prefs.contains(KEY_LAST_SEEN_ELAPSED)) {
            prefs.getLong(KEY_LAST_SEEN_ELAPSED, 0L)
        } else null

    /** `System.currentTimeMillis()` at the last interaction, or null if none. */
    val lastSeenWall: Long?
        get() = if (prefs.contains(KEY_LAST_SEEN_WALL)) {
            prefs.getLong(KEY_LAST_SEEN_WALL, 0L)
        } else null

    /**
     * Stores both clocks together, in one edit.
     *
     * Two readings because neither clock alone can answer "how long has this
     * session been untouched": `elapsedRealtime` counts time the device spent
     * asleep but restarts at zero on every boot, while the wall clock survives a
     * reboot but can be moved by the user or by NTP. Written as a pair so a
     * process death between two separate edits cannot leave one fresh mark
     * beside one stale one — which would read as a session that was just used.
     */
    fun recordLastSeen(elapsed: Long, wall: Long) {
        prefs.edit()
            .putLong(KEY_LAST_SEEN_ELAPSED, elapsed)
            .putLong(KEY_LAST_SEEN_WALL, wall)
            .apply()
    }

    /**
     * Forgets when the user was last seen, so nothing can answer "how long has
     * this session been idle" any more.
     *
     * Written when the app locks itself: the answer must not survive the lock,
     * because a mark left behind would tell the next launch — after the process
     * was killed with the lock on screen — that the session had just been used.
     */
    fun clearLastSeen() {
        prefs.edit()
            .remove(KEY_LAST_SEEN_ELAPSED)
            .remove(KEY_LAST_SEEN_WALL)
            .apply()
    }

    /** Drops only the session tokens — device identity and settings survive. */
    fun clearTokens() {
        prefs.edit()
            .remove(KEY_ACCESS_TOKEN)
            .remove(KEY_REFRESH_TOKEN)
            .apply()
    }

    /**
     * Wipes the signed-in session: tokens, the cached user identity and the
     * biometric opt-in (enrollment is per-user, so the next user must opt in
     * again rather than inherit this one's).
     *
     * Three keys deliberately survive, because they are device state rather
     * than session state and dropping them breaks the device permanently:
     *
     *  - [KEY_DB_PASSPHRASE] is the SQLCipher key. The encrypted database
     *    file outlives a logout, so minting a new passphrase would leave a
     *    file no key can open — every Room access afterwards throws
     *    "file is not a database". Callers wipe the *contents* instead
     *    (SecureMedDao.clearAll).
     *  - [KEY_DEVICE_ID] is registered server-side by biometric enrollment.
     *    A new id makes the backend treat this device as unknown, so
     *    biometric login can never succeed again.
     *  - [KEY_INSTALL_ID] is the `X-Device-Fingerprint` this install sends.
     *    A new value is a new device to the backend: adaptive MFA challenges
     *    the login again, the "trusted device" row it earned is orphaned, and
     *    a fingerprint that changes *mid-session* is what the server's hijack
     *    detection is built to catch.
     */
    fun clearSession() {
        prefs.edit()
            .remove(KEY_ACCESS_TOKEN)
            .remove(KEY_REFRESH_TOKEN)
            .remove(KEY_USER_ID)
            .remove(KEY_USER_EMAIL)
            .remove(KEY_USER_NAME)
            .remove(KEY_USER_ROLE)
            .remove(KEY_BIOMETRIC_ENABLED)
            // Idle marks belong to the session that has just ended. Left behind,
            // they would answer "how long since the last interaction" for a user
            // who is no longer signed in. [idleTimeoutMinutes] is a preference,
            // not session state, so it deliberately stays.
            .remove(KEY_LAST_SEEN_ELAPSED)
            .remove(KEY_LAST_SEEN_WALL)
            .apply()
    }

    /**
     * Last-resort wipe for the tamper path ([com.securemed.app.security.SecureWipe]):
     * drops the device-bound identities too, not just the session keys.
     *
     * Deliberately separate from [clearSession] — an ordinary logout keeps
     * [deviceId]/[installId] so the trusted-device row and the biometric
     * enrollment survive, but a device that reported instrumentation is one
     * whose identities we no longer trust.
     *
     * Synchronous `commit()`: the process may be killed the moment the
     * caller decides to wipe, and an async write landing after that would
     * resurrect exactly the state we are trying to destroy.
     */
    fun clearAllForWipe() {
        cachedInstallId = null
        prefs.edit().clear().commit()
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

    /**
     * Stable per-install identifier sent as `X-Device-Fingerprint`.
     *
     * The backend keys real security decisions on this string: the trusted-device
     * row that lets adaptive MFA stop challenging this phone
     * (`DeviceRegistry.is_trusted`), the escalating per-device lockout after five
     * failed logins (`BlockedDevice`), the WAF's device blocklist, and the
     * fingerprint recorded with the session. Three properties follow from that,
     * and each of them is a bug if it is missing:
     *
     *  - **Unguessable.** 32 bytes from [java.security.SecureRandom], not
     *    `ANDROID_ID` and not a timestamp. A guessable value lets an attacker
     *    inherit a device's trusted status, or get someone else's phone locked
     *    out by failing five logins under their fingerprint.
     *  - **One value per process.** Minted under a lock and cached, because
     *    OkHttp can be on two requests at once on first launch: two threads each
     *    minting their own id would send two fingerprints for one device, and a
     *    fingerprint that changes inside a live session is exactly what the
     *    server's hijack detection revokes the session for.
     *  - **Written synchronously.** `commit()`, not `apply()`: a process death
     *    between minting and the async write landing would mint a *different* id
     *    on the next launch, re-challenging the user and stranding the trusted
     *    row on a fingerprint nothing sends any more.
     *
     * Deliberately not `ANDROID_ID`: it is not resettable by the user, it lets
     * unrelated apps correlate this install, and it is unavailable behind a work
     * profile — while a random value costs nothing and survives exactly as long
     * as the install does.
     */
    val installId: String
        get() {
            cachedInstallId?.let { return it }
            return synchronized(this) {
                // Re-check inside the lock: another thread may have minted while
                // this one waited.
                cachedInstallId ?: run {
                    val stored = prefs.getString(KEY_INSTALL_ID, null)
                    val id = if (stored.isNullOrBlank()) {
                        val bytes = ByteArray(32)
                        java.security.SecureRandom().nextBytes(bytes)
                        // Locale.ROOT: on an Arabic-locale device a localizing
                        // formatter would be free to emit Arabic-Indic digits,
                        // and a non-ASCII byte in an HTTP header value makes
                        // OkHttp throw on every single request.
                        val minted = bytes.joinToString("") {
                            String.format(java.util.Locale.ROOT, "%02x", it)
                        }
                        prefs.edit().putString(KEY_INSTALL_ID, minted).commit()
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

    fun getDatabasePassphrase(): ByteArray {
        var passphrase = prefs.getString(KEY_DB_PASSPHRASE, null)
        if (passphrase == null) {
            passphrase = java.util.UUID.randomUUID().toString()
            prefs.edit().putString(KEY_DB_PASSPHRASE, passphrase).apply()
        }
        return passphrase.toByteArray()
    }
}
