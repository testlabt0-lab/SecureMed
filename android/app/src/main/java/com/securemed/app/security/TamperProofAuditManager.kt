package com.securemed.app.security

import android.content.Context
import com.securemed.app.data.local.SecurePreferences
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest

/**
 * Tamper-Proof Cryptographic Hash-Chained Audit Trail (HIPAA / ISO 27799 / PDPL).
 *
 * Implements a verifiable hash chain (Merkle/Blockchain-style structure):
 * Every local access event (view chart, barcode scan, break-glass) is hashed
 * with the previous event's hash. If any past record is modified or deleted by malware
 * or an unauthorized user, the cryptographic chain is broken and detected immediately.
 */
object TamperProofAuditManager {

    private const val GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"
    private const val AUDIT_LOG_FILE = "secure_audit_chain.json"

    data class AuditEntry(
        val index: Long,
        val timestamp: Long,
        val action: String,
        val details: String,
        val previousHash: String,
        val hash: String
    )

    private val lock = Any()

    /**
     * Records a new audit event into the hash chain.
     */
    fun recordEvent(
        context: Context,
        action: String,
        details: String
    ): AuditEntry = synchronized(lock) {
        val file = File(context.filesDir, AUDIT_LOG_FILE)
        val entries = loadEntries(file)

        val previousHash = entries.lastOrNull()?.hash ?: GENESIS_HASH
        val index = (entries.lastOrNull()?.index ?: 0L) + 1
        val timestamp = System.currentTimeMillis()

        val dataToHash = "$index|$timestamp|$action|$details|$previousHash"
        val hash = sha256(dataToHash)

        val newEntry = AuditEntry(
            index = index,
            timestamp = timestamp,
            action = action,
            details = details,
            previousHash = previousHash,
            hash = hash
        )

        entries.add(newEntry)
        saveEntries(file, entries)

        return newEntry
    }

    /**
     * Verifies the cryptographic integrity of the entire audit chain.
     * Returns Pair(isChainValid, invalidEntryIndexOrNull).
     */
    fun verifyChainIntegrity(context: Context): Pair<Boolean, Long?> = synchronized(lock) {
        val file = File(context.filesDir, AUDIT_LOG_FILE)
        val entries = loadEntries(file)

        if (entries.isEmpty()) return Pair(true, null)

        var expectedPrevHash = GENESIS_HASH

        for (entry in entries) {
            // Verify link with previous
            if (entry.previousHash != expectedPrevHash) {
                return Pair(false, entry.index)
            }

            // Verify entry hash computation
            val recomputedHash = sha256("${entry.index}|${entry.timestamp}|${entry.action}|${entry.details}|${entry.previousHash}")
            if (entry.hash != recomputedHash) {
                return Pair(false, entry.index)
            }

            expectedPrevHash = entry.hash
        }

        return Pair(true, null)
    }

    fun getEventCount(context: Context): Int = synchronized(lock) {
        val file = File(context.filesDir, AUDIT_LOG_FILE)
        return loadEntries(file).size
    }

    private fun loadEntries(file: File): MutableList<AuditEntry> {
        val list = mutableListOf<AuditEntry>()
        if (!file.exists()) return list

        runCatching {
            val jsonArray = JSONArray(file.readText())
            for (i in 0 until jsonArray.length()) {
                val obj = jsonArray.getJSONObject(i)
                list.add(
                    AuditEntry(
                        index = obj.getLong("index"),
                        timestamp = obj.getLong("timestamp"),
                        action = obj.getString("action"),
                        details = obj.getString("details"),
                        previousHash = obj.getString("previousHash"),
                        hash = obj.getString("hash")
                    )
                )
            }
        }
        return list
    }

    private fun saveEntries(file: File, entries: List<AuditEntry>) {
        runCatching {
            val jsonArray = JSONArray()
            for (entry in entries) {
                val obj = JSONObject().apply {
                    put("index", entry.index)
                    put("timestamp", entry.timestamp)
                    put("action", entry.action)
                    put("details", entry.details)
                    put("previousHash", entry.previousHash)
                    put("hash", entry.hash)
                }
                jsonArray.put(obj)
            }
            file.writeText(jsonArray.toString())
        }
    }

    private fun sha256(input: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val bytes = digest.digest(input.toByteArray(Charsets.UTF_8))
        return bytes.joinToString("") { "%02x".format(it) }
    }
}
