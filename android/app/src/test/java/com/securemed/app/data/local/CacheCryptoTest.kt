package com.securemed.app.data.local

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey

/**
 * Unit tests for the cache envelope in [CacheCrypto] (4-1).
 *
 * The keystore is Android-only, so every test drives the explicit-key seam
 * ([CacheCrypto.seal]/[CacheCrypto.open]) with a software AES-256 key — the
 * exact byte paths `encrypt`/`decrypt` run on the device, minus the keystore
 * lookup. What is pinned: round-trip, envelope recognition, and the failure
 * contract (null, never a throw, never plaintext fallback).
 */
class CacheCryptoTest {

    private fun softwareKey(): SecretKey =
        KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()

    @Test
    fun `seal and open round-trip the plaintext`() {
        val key = softwareKey()
        val plaintext = """{"medication_plans":[{"id":"x","name":"أموكسيسيلين","patient_name":"مريض"}]}"""

        val sealed = CacheCrypto.seal(key, plaintext)!!

        assertTrue(CacheCrypto.looksEncrypted(sealed))
        assertEquals(plaintext, CacheCrypto.open(key, sealed))
    }

    @Test
    fun `looksEncrypted rejects a legacy plaintext file`() {
        val legacy = """{"key": "value"}""".toByteArray(Charsets.UTF_8)

        assertFalse(CacheCrypto.looksEncrypted(legacy))
    }

    @Test
    fun `open returns null for a corrupted envelope`() {
        val key = softwareKey()
        val sealed = CacheCrypto.seal(key, "بيانات سريرية محمية")!!

        // Flip a byte inside the ciphertext body — the GCM tag must reject it.
        sealed[sealed.size - 1] = (sealed[sealed.size - 1].toInt() xor 0x01).toByte()

        assertNull(CacheCrypto.open(key, sealed))
    }

    @Test
    fun `open returns null when the key does not match the envelope`() {
        val sealed = CacheCrypto.seal(softwareKey(), "سر")!!
        val wrongKey = softwareKey()

        assertNull(CacheCrypto.open(wrongKey, sealed))
    }

    @Test
    fun `open returns null for a truncated envelope`() {
        val key = softwareKey()
        val sealed = CacheCrypto.seal(key, "قابل للقطع")!!

        assertNull(CacheCrypto.open(key, sealed.copyOfRange(0, sealed.size - 5)))
    }
}
