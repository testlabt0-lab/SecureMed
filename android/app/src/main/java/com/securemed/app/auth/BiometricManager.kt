package com.securemed.app.auth

import android.content.Context
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import java.util.concurrent.Executor

/**
 * Biometric Manager - handles fingerprint authentication.
 *
 * Security requirement #4: تسجيل الدخول بالبصمة + الاعتماد على البصمة
 * Uses AndroidX Biometric API for secure authentication.
 */
class BiometricManager(private val context: Context) {

    private val executor: Executor = ContextCompat.getMainExecutor(context)
    private val biometricManager = BiometricManager.from(context)

    /**
     * Check if biometric authentication is available on the device.
     */
    fun isBiometricAvailable(): Boolean {
        return biometricManager.canAuthenticate(
            BiometricManager.Authenticators.BIOMETRIC_STRONG
        ) == BiometricManager.BIOMETRIC_SUCCESS
    }

    /**
     * Generate a unique biometric template identifier.
     * In production, this would integrate with BiometricPrompt.CryptoObject
     * to sign a challenge with the biometric-protected key.
     */
    fun generateBiometricTemplate(userId: String): String {
        return "android-bio-$userId-${System.currentTimeMillis()}-${(0..9999).random()}"
    }

    /**
     * Show biometric prompt for authentication.
     */
    fun authenticate(
        activity: FragmentActivity,
        title: String,
        subtitle: String,
        description: String,
        cryptoObject: BiometricPrompt.CryptoObject?,
        onSuccess: (BiometricPrompt.AuthenticationResult) -> Unit,
        onError: (String) -> Unit,
        onCancel: () -> Unit
    ) {
        val promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle(title)
            .setSubtitle(subtitle)
            .setDescription(description)
            .setNegativeButtonText("إلغاء")
            .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG)
            .setConfirmationRequired(false)
            .build()

        val prompt = BiometricPrompt(activity, executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    // Return the result containing the unlocked CryptoObject
                    onSuccess(result)
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    when (errorCode) {
                        BiometricPrompt.ERROR_USER_CANCELED,
                        BiometricPrompt.ERROR_NEGATIVE_BUTTON,
                        BiometricPrompt.ERROR_CANCELED -> onCancel()
                        else -> onError(errString.toString())
                    }
                }

                override fun onAuthenticationFailed() {
                    // Called on each failed attempt (e.g., wrong finger)
                    // Don't call onError here - wait for final error
                }
            }
        )
        
        if (cryptoObject != null) {
            prompt.authenticate(promptInfo, cryptoObject)
        } else {
            prompt.authenticate(promptInfo)
        }
    }
}

/**
 * Helper to access SecurePreferences without circular dependency.
 */
private object SecurePreferencesHelper {
    fun getUserId(): String? = com.securemed.app.data.local.SecurePreferences.userId
}
