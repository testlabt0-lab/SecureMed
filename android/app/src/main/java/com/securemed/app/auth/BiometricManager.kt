package com.securemed.app.auth

import android.content.Context
import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyPermanentlyInvalidatedException
import android.security.keystore.KeyProperties
import android.util.Base64
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import java.security.KeyStore
import java.security.Signature
import java.security.KeyPairGenerator
import java.security.PrivateKey
import java.util.concurrent.Executor

/**
 * Biometric Manager — real biometric-bound authentication.
 *
 * Security requirement #4: تسجيل الدخول بالبصمة + الاعتماد على البصمة
 *
 * Architecture (challenge → sign → verify):
 *  1. ENROLLMENT: an EC key pair is generated inside the Android Keystore
 *     marked `setUserAuthenticationRequired(true)` — the private key can
 *     only be used after a successful fingerprint scan. The PUBLIC key is
 *     submitted to the server (never any biometric data).
 *  2. LOGIN: the server sends a random one-time challenge; the fingerprint
 *     unlocks the private key through `BiometricPrompt.CryptoObject`, the
 *     device signs the challenge (ECDSA-SHA256) and the server verifies the
 *     signature with the enrolled public key.
 *
 * This makes fingerprint login a genuine proof of possession: the JWT is
 * only issued when the enrolled fingerprint holder is physically present.
 */
class BiometricManager(private val context: Context) {

    companion object {
        private const val KEYSTORE = "AndroidKeyStore"
        private const val KEY_ALIAS = "securemed_biometric_key"
    }

    private val executor: Executor = ContextCompat.getMainExecutor(context)
    private val biometricManager = BiometricManager.from(context)

    /** Whether the device has a compatible biometric sensor with enrolled samples. */
    fun isBiometricAvailable(): Boolean =
        canAuthenticate() == BiometricManager.BIOMETRIC_SUCCESS

    /** Arabic explanation of why biometrics are unavailable right now. */
    fun availabilityMessage(): String = when (canAuthenticate()) {
        BiometricManager.BIOMETRIC_SUCCESS -> "البصمة متاحة"
        BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED ->
            "لا توجد بصمة مسجلة — أضف بصمتك من إعدادات الجهاز أولاً"
        BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE -> "البصمة غير متاحة على هذا الجهاز"
        BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE ->
            "مستشعر البصمة غير متاح حالياً — أعد المحاولة لاحقاً"
        BiometricManager.BIOMETRIC_ERROR_SECURITY_UPDATE_REQUIRED ->
            "يتطلب تحديثاً أمنياً للجهاز"
        else -> "البصمة غير متاحة"
    }

    private fun canAuthenticate(): Int =
        biometricManager.canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG)

    // ------------------------------------------------------------------
    // Keystore signing key management
    // ------------------------------------------------------------------

    /** True when a usable biometric-bound signing key exists. */
    fun hasSigningKey(): Boolean = try {
        val keyStore = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        keyStore.containsAlias(KEY_ALIAS)
    } catch (_: Exception) {
        false
    }

    /**
     * Create the Keystore key pair if missing (or recreate after
     * invalidation). Returns true when the key is ready to sign.
     */
    fun ensureSigningKey(): Boolean {
        return try {
            val keyStore = KeyStore.getInstance(KEYSTORE).apply { load(null) }
            if (!keyStore.containsAlias(KEY_ALIAS)) {
                generateKeyPair()
            }
            true
        } catch (_: Exception) {
            false
        }
    }

    private fun generateKeyPair() {
        val generator = KeyPairGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_EC, KEYSTORE
        )
        val builder = KeyGenParameterSpec.Builder(
            KEY_ALIAS,
            KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY
        )
            .setDigests(KeyProperties.DIGEST_SHA256)
            .setUserAuthenticationRequired(true)
        // NOTE: EC keys use no signature padding — "SHA256withECDSA" only
        // needs the SHA-256 digest.

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            // 30 seconds grace window after a successful fingerprint scan
            builder.setUserAuthenticationParameters(
                30,
                KeyProperties.AUTH_BIOMETRIC_STRONG
            )
        } else {
            @Suppress("DEPRECATION")
            builder.setUserAuthenticationValidityDurationSeconds(30)
        }

        generator.initialize(builder.build())
        generator.generateKeyPair()
    }

    /**
     * The public key (base64 DER SubjectPublicKeyInfo) to submit during
     * enrollment. Returns null when the key does not exist.
     */
    fun getPublicKeyBase64(): String? {
        return try {
            val keyStore = KeyStore.getInstance(KEYSTORE).apply { load(null) }
            val cert = keyStore.getCertificate(KEY_ALIAS) ?: return null
            Base64.encodeToString(cert.publicKey.encoded, Base64.NO_WRAP)
        } catch (_: Exception) {
            null
        }
    }

    private fun getPrivateKey(): PrivateKey? = try {
        val keyStore = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        (keyStore.getKey(KEY_ALIAS, null) as? PrivateKey)
    } catch (_: Exception) {
        null
    }

    /** Delete the key (used after invalidation — requires re-enrollment). */
    fun deleteSigningKey() {
        try {
            val keyStore = KeyStore.getInstance(KEYSTORE).apply { load(null) }
            if (keyStore.containsAlias(KEY_ALIAS)) {
                keyStore.deleteEntry(KEY_ALIAS)
            }
        } catch (_: Exception) {
        }
    }

    // ------------------------------------------------------------------
    // Biometric prompt with CryptoObject (signature mode)
    // ------------------------------------------------------------------

    /**
     * Show the fingerprint prompt bound to a signing operation. On success
     * the [challenge] is signed with the Keystore key and the base64
     * signature is delivered to [onSuccess].
     */
    fun signChallenge(
        activity: FragmentActivity,
        challenge: String,
        title: String,
        subtitle: String,
        description: String,
        onSuccess: (String) -> Unit,
        onError: (String) -> Unit,
        onCancel: () -> Unit
    ) {
        if (!ensureSigningKey()) {
            onError("تعذر إنشاء مفتاح التوقيع الآمن على هذا الجهاز")
            return
        }

        val privateKey = getPrivateKey()
        if (privateKey == null) {
            onError("مفتاح المصادقة مفقود — أعد تسجيل البصمة من الملف الشخصي")
            return
        }

        val signature: Signature = try {
            Signature.getInstance("SHA256withECDSA").apply {
                initSign(privateKey)
            }
        } catch (e: KeyPermanentlyInvalidatedException) {
            deleteSigningKey()
            onError("تغيرت بصمات الجهاز — أعد تسجيل البصمة من الملف الشخصي")
            return
        } catch (e: Exception) {
            onError("فشل تجهيز مفتاح التوقيع: ${e.message}")
            return
        }

        val promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle(title)
            .setSubtitle(subtitle)
            .setDescription(description)
            .setNegativeButtonText("إلغاء")
            .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG)
            .build()

        val prompt = BiometricPrompt(
            activity,
            executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(
                    result: BiometricPrompt.AuthenticationResult
                ) {
                    try {
                        val cryptoSignature =
                            result.cryptoObject?.signature ?: signature
                        cryptoSignature.update(challenge.toByteArray(Charsets.UTF_8))
                        val signed = cryptoSignature.sign()
                        onSuccess(Base64.encodeToString(signed, Base64.NO_WRAP))
                    } catch (e: Exception) {
                        onError("فشل توقيع التحدي: ${e.message}")
                    }
                }

                override fun onAuthenticationError(
                    errorCode: Int,
                    errString: CharSequence
                ) {
                    when (errorCode) {
                        BiometricPrompt.ERROR_USER_CANCELED,
                        BiometricPrompt.ERROR_NEGATIVE_BUTTON,
                        BiometricPrompt.ERROR_CANCELED -> onCancel()
                        else -> onError(errString.toString())
                    }
                }

                override fun onAuthenticationFailed() {
                    // Wrong finger — keep waiting for the next attempt.
                }
            }
        )
        prompt.authenticate(promptInfo, BiometricPrompt.CryptoObject(signature))
    }
}
