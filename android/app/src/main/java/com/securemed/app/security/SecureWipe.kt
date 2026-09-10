package com.securemed.app.security

import android.content.Context
import com.securemed.app.data.local.LocalCache
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.data.local.room.SecureMedDatabase
import java.io.File
import java.security.SecureRandom

/**
 * Securely erases every local trace of a session.
 *
 * Deleting a file only unlinks it — the bytes stay on flash until the sector
 * is reallocated, and on a phone that gets resold or seized the "deleted"
 * PHI is recoverable with ordinary tools. This wipes the *contents* first,
 * then unlinks, for each store that holds patient or session data:
 *
 *  * the Room database (SQLCipher — contents wiped, then file deleted),
 *  * the offline cache (AES-GCM sealed — wiped entry by entry),
 *  * the encrypted preferences (session keys dropped by [SecurePreferences],
 *    contents overwritten).
 *
 * The DB passphrase in the preferences is deliberately wiped *after* the
 * database contents, so a crash mid-wipe leaves the encrypted file (whose key
 * is being destroyed) rather than an orphan plaintext.
 */
object SecureWipe {

    /**
     * Wipes session data, keeping the device-bound identity
     * ([SecurePreferences.installId]) — it survives a logout
     * on purpose (see [SecurePreferences.clearSession]); dropping it would
     * orphan the server-side biometric enrollment and trusted-device row.
     */
    fun wipeSession(context: Context) {
        val dbFile = context.getDatabasePath(SecureMedDatabase.DATABASE_NAME)
        wipeDirContents(dbFile.parentFile?.takeIf { it.exists() })
        wipeDirContents(File(context.filesDir, "offline_cache"))
        SecurePreferences.clearSession()
        LocalCache.clear()
    }

    /**
     * Nukes everything, including the device identity, for the "wipe on
     * tamper" path: a device we believe is compromised should not keep any
     * identity an attacker could reuse.
     */
    fun wipeEverything(context: Context) {
        wipeSession(context)
        SecurePreferences.clearAllForWipe()
    }

    /**
     * Overwrite every file in a directory with random bytes, then unlink it.
     *
     * Flash translation layers ignore overwrites to remapped sectors, so
     * this is defence in depth rather than a guarantee; it costs almost
     * nothing and defeats the casual file-recovery tools that would
     * otherwise see the whole plaintext database.
     */
    private fun wipeDirContents(dir: File?) {
        if (dir == null || !dir.exists()) return
        val random = SecureRandom()
        dir.listFiles()?.forEach { file ->
            runCatching {
                if (file.isFile && file.length() > 0) {
                    val bytes = ByteArray(file.length().toInt().coerceAtMost(4 shl 20))
                    random.nextBytes(bytes)
                    file.outputStream().use { it.write(bytes) }
                }
                file.delete()
            }
        }
    }
}
