package com.securemed.app.security

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Hardware-backed Cryptographic Manager for SecureMed.
 *
 * Utilizes Android Hardware Keystore with StrongBox Keymaster (dedicated physical
 * security chip like Titan M2 / Samsung Knox Vault) when available on the device,
 * providing the highest hardware resistance against memory-dump and physical extraction attacks.
 */
object HardwareCryptoManager {

    private const val ANDROID_KEYSTORE = "AndroidKeyStore"
    private const val MASTER_KEY_ALIAS = "securemed_hardware_master_key"
    private const val GCM_TAG_LENGTH = 128

    /**
     * Checks if the device has a dedicated hardware security module (StrongBox).
     */
    fun isStrongBoxSupported(context: Context): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            context.packageManager.hasSystemFeature(PackageManager.FEATURE_STRONGBOX_KEYSTORE)
        } else {
            false
        }
    }

    /**
     * Returns human-readable hardware security classification of the device.
     */
    fun getHardwareSecurityLevel(context: Context): String {
        return if (isStrongBoxSupported(context)) {
            "شريحة أمان مادية مستقلة (StrongBox Hardware HSM)"
        } else {
            "بيئة تنفيذ معزولة عتادية (Hardware-backed TEE)"
        }
    }

    /**
     * Gets or generates the hardware-backed AES-256 key.
     */
    @Synchronized
    fun getOrCreateHardwareKey(context: Context): SecretKey {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }

        if (keyStore.containsAlias(MASTER_KEY_ALIAS)) {
            val entry = keyStore.getEntry(MASTER_KEY_ALIAS, null) as? KeyStore.SecretKeyEntry
            if (entry != null) return entry.secretKey
        }

        // Generate a new hardware-bound key
        val keyGenerator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)

        val builder = KeyGenParameterSpec.Builder(
            MASTER_KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)

        // Attempt StrongBox hardware security chip if supported
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P && isStrongBoxSupported(context)) {
            try {
                builder.setIsStrongBoxBacked(true)
                keyGenerator.init(builder.build())
                return keyGenerator.generateKey()
            } catch (e: Exception) {
                android.util.Log.w("HardwareCrypto", "StrongBox allocation failed, falling back to TEE", e)
            }
        }

        // Fallback to standard hardware-backed TEE KeyStore
        val teeBuilder = KeyGenParameterSpec.Builder(
            MASTER_KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)

        keyGenerator.init(teeBuilder.build())
        return keyGenerator.generateKey()
    }

    /**
     * Encrypts plaintext using AES-256-GCM backed by hardware Keystore.
     * Returns Pair(IV, CipherText).
     */
    fun encrypt(context: Context, plaintext: ByteArray): Pair<ByteArray, ByteArray> {
        val key = getOrCreateHardwareKey(context)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key)
        val iv = cipher.iv
        val ciphertext = cipher.doFinal(plaintext)
        return Pair(iv, ciphertext)
    }

    /**
     * Decrypts ciphertext using AES-256-GCM and the hardware Keystore key.
     */
    fun decrypt(context: Context, iv: ByteArray, ciphertext: ByteArray): ByteArray {
        val key = getOrCreateHardwareKey(context)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        val spec = GCMParameterSpec(GCM_TAG_LENGTH, iv)
        cipher.init(Cipher.DECRYPT_MODE, key, spec)
        return cipher.doFinal(ciphertext)
    }
}
