package com.securemed.app.security

import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyPermanentlyInvalidatedException
import android.security.keystore.KeyProperties
import android.util.Base64
import android.util.Log
import androidx.biometric.BiometricPrompt
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.PrivateKey
import java.security.Signature
import java.security.spec.ECGenParameterSpec

/**
 * The device's biometric signing key.
 *
 * Security requirement #4: تسجيل الدخول بالبصمة + الاعتماد على البصمة
 *
 * What stood here before could not authenticate anything. The key was a
 * symmetric `AES/CBC/PKCS7` secret and login sent `IV:ciphertext` of a locally
 * invented string as `biometric_template`. The server holds no copy of that
 * secret, so it could not check the ciphertext — and even if it could, anyone
 * who never touches the sensor can post any string he likes. Possession of a
 * key held in the Keystore can only be *proved* to a remote party by signing a
 * value that remote party chose.
 *
 * So: an EC P-256 key pair whose private half is generated inside the Keystore
 * (it has no exportable form and never appears in app memory), created with
 * `setUserAuthenticationRequired(true)`, which makes the Keystore refuse to
 * sign until a class-3 biometric has unlocked it for that one operation. The
 * server keeps the public half — `publicKey.encoded` is SPKI DER, exactly what
 * the backend's `load_public_key()` reads — and checks a `SHA256withECDSA`
 * signature over the raw challenge bytes in `verify_native_assertion()`.
 *
 * `setInvalidatedByBiometricEnrollment(true)` is deliberate: adding a
 * fingerprint destroys the key, so someone who adds their own finger to an
 * unlocked phone cannot inherit an enrollment made with the owner's. The cost
 * is that the owner must enroll again, which is what [Unlock.Invalidated] tells
 * the UI to ask for.
 */
object BiometricHelper {

    private const val TAG = "BiometricHelper"

    /**
     * A new alias, not the old `securemed_biometric_key`. Devices that ran the
     * previous build still hold an AES secret under that name, and reusing it
     * would hand `getKey()` a `SecretKey` where a `PrivateKey` is expected —
     * a ClassCastException on every login attempt.
     */
    private const val KEY_NAME = "securemed_biometric_ec_p256"
    private const val ANDROID_KEYSTORE = "AndroidKeyStore"
    private const val SIGNATURE_ALGORITHM = "SHA256withECDSA"

    /** Unpadded base64url — the only encoding the backend's b64url_decode reads. */
    private const val B64URL = Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING

    /** The outcome of preparing the signing key for one assertion. */
    sealed class Unlock {
        data class Ready(val cryptoObject: BiometricPrompt.CryptoObject) : Unlock()

        /** No key on this device: this account never enrolled here. */
        data object NotEnrolled : Unlock()

        /** Fingerprints changed after enrollment, so the Keystore erased the key. */
        data object Invalidated : Unlock()

        data class Failed(val message: String) : Unlock()
    }

    private fun keyStore(): KeyStore =
        KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }

    /** Whether this device still holds a usable enrollment key. */
    fun hasKey(): Boolean = try {
        keyStore().containsAlias(KEY_NAME)
    } catch (e: Exception) {
        Log.e(TAG, "Keystore unreadable", e)
        false
    }

    fun deleteKey() {
        try {
            keyStore().deleteEntry(KEY_NAME)
        } catch (e: Exception) {
            Log.e(TAG, "Could not delete the signing key", e)
        }
    }

    /**
     * Generate the enrollment key pair and return its public half as base64url
     * SPKI DER — the `public_key` field of POST /auth/biometric/enroll/.
     *
     * Generation is not gated by the prompt (only *use* is), so this needs no UI.
     * Any earlier key is dropped first: the server stores one public key per
     * (user, device), so a second private key could only produce signatures that
     * nothing on the server can verify.
     */
    fun createSigningKey(): String? = try {
        deleteKey()
        val generator = KeyPairGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_EC, ANDROID_KEYSTORE
        )
        generator.initialize(keySpec())
        Base64.encodeToString(generator.generateKeyPair().public.encoded, B64URL)
    } catch (e: Exception) {
        Log.e(TAG, "Signing key generation failed", e)
        null
    }

    private fun keySpec(): KeyGenParameterSpec =
        KeyGenParameterSpec.Builder(KEY_NAME, KeyProperties.PURPOSE_SIGN)
            .setAlgorithmParameterSpec(ECGenParameterSpec("secp256r1"))
            .setDigests(KeyProperties.DIGEST_SHA256)
            .setUserAuthenticationRequired(true)
            .setInvalidatedByBiometricEnrollment(true)
            .apply {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                    // Timeout 0 means authenticate for every single use, and
                    // only a class-3 biometric counts — the device PIN must not
                    // stand in for the finger. Below API 30 this is already the
                    // default, since no validity duration is set.
                    setUserAuthenticationParameters(
                        0, KeyProperties.AUTH_BIOMETRIC_STRONG
                    )
                }
            }
            .build()

    /**
     * Initialise a [Signature] with the private key and wrap it for the prompt.
     *
     * `initSign` is where the Keystore reports that the key is gone or no longer
     * valid. The biometric gate itself is applied later, at `sign()`, and only
     * because the prompt handed this very object back after verifying a finger.
     */
    fun unlockForSigning(): Unlock = try {
        val privateKey = keyStore().getKey(KEY_NAME, null) as? PrivateKey
        if (privateKey == null) {
            Unlock.NotEnrolled
        } else {
            val signature = Signature.getInstance(SIGNATURE_ALGORITHM)
            signature.initSign(privateKey)
            Unlock.Ready(BiometricPrompt.CryptoObject(signature))
        }
    } catch (e: KeyPermanentlyInvalidatedException) {
        Log.w(TAG, "Signing key invalidated by a biometric change", e)
        deleteKey()
        Unlock.Invalidated
    } catch (e: Exception) {
        Log.e(TAG, "Could not prepare the signing key", e)
        Unlock.Failed(e.message ?: "تعذر تهيئة مفتاح البصمة")
    }

    /**
     * Sign the server's challenge with the [Signature] the prompt just unlocked.
     *
     * What gets signed is the decoded challenge and nothing else — no prefix, no
     * timestamp, no locally built string — because that is precisely what
     * `verify_native_assertion()` verifies. The result is an ASN.1 DER (r,s)
     * sequence, the encoding `cryptography` expects for ES256.
     *
     * This throws instead of returning a placeholder. The old `encryptChallenge`
     * answered failure with the literal text "encryption-failed" and posted it
     * to the server as though it were a credential.
     */
    fun signChallenge(signature: Signature, challengeB64Url: String): String {
        signature.update(decodeB64Url(challengeB64Url))
        return Base64.encodeToString(signature.sign(), B64URL)
    }

    /** Decode unpadded base64url; Android's decoder wants the padding back. */
    private fun decodeB64Url(text: String): ByteArray {
        val trimmed = text.trim()
        val padded = trimmed + "=".repeat((4 - trimmed.length % 4) % 4)
        return Base64.decode(padded, Base64.URL_SAFE or Base64.NO_WRAP)
    }
}
