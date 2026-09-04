package com.securemed.app.security

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey

object BiometricHelper {

    private const val KEY_NAME = "securemed_biometric_key"
    private const val ANDROID_KEYSTORE = "AndroidKeyStore"

    fun getCryptoObject(): androidx.biometric.BiometricPrompt.CryptoObject? {
        return try {
            val cipher = getCipher()
            val secretKey = getSecretKey()
            cipher.init(Cipher.ENCRYPT_MODE, secretKey)
            androidx.biometric.BiometricPrompt.CryptoObject(cipher)
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    private fun getCipher(): Cipher {
        return Cipher.getInstance(
            KeyProperties.KEY_ALGORITHM_AES + "/"
                    + KeyProperties.BLOCK_MODE_CBC + "/"
                    + KeyProperties.ENCRYPTION_PADDING_PKCS7
        )
    }

    private fun getSecretKey(): SecretKey {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
        keyStore.load(null)
        if (!keyStore.containsAlias(KEY_NAME)) {
            generateSecretKey()
        }
        return keyStore.getKey(KEY_NAME, null) as SecretKey
    }

    private fun generateSecretKey() {
        val keyGenerator = KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES,
            ANDROID_KEYSTORE
        )
        val keyGenParameterSpec = KeyGenParameterSpec.Builder(
            KEY_NAME,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_CBC)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_PKCS7)
            .setUserAuthenticationRequired(true) // Key is only accessible when user authenticates
            // .setUserAuthenticationValidityDurationSeconds(10) // Optional time validity
            .build()
        keyGenerator.init(keyGenParameterSpec)
        keyGenerator.generateKey()
    }
    
    /**
     * Encrypts a challenge using the unlocked Cipher.
     * The result is Base64 encoded: "IV:Ciphertext"
     */
    fun encryptChallenge(cipher: Cipher, challenge: String): String {
        return try {
            val encryptedBytes = cipher.doFinal(challenge.toByteArray(Charsets.UTF_8))
            val iv = cipher.iv
            val ivBase64 = android.util.Base64.encodeToString(iv, android.util.Base64.NO_WRAP)
            val cipherBase64 = android.util.Base64.encodeToString(encryptedBytes, android.util.Base64.NO_WRAP)
            "$ivBase64:$cipherBase64"
        } catch (e: Exception) {
            e.printStackTrace()
            "encryption-failed"
        }
    }
}
