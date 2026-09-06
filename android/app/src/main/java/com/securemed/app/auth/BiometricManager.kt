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
     * Show the biometric prompt.
     *
     * When [cryptoObject] is supplied the prompt is bound to it, and only then
     * does success mean anything cryptographic: `BIOMETRIC_STRONG` plus a
     * Keystore key created with `setUserAuthenticationRequired(true)` is what
     * releases the private key for exactly one signature. Without a
     * CryptoObject the callback merely reports that the OS was satisfied — the
     * app cannot prove that to anyone else, which is why login always passes one.
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

    /**
     * Authenticators accepted for unlocking the app after an idle timeout:
     * a class-3 biometric, or the device PIN/pattern/password.
     *
     * The device credential is included because a fingerprint is not always
     * available — a wet or bandaged finger, a phone with none enrolled — and an
     * idle lock the owner cannot open would cost them their unsaved work.
     *
     * Combining the two is only expressible this way from API 30. On 26-29
     * androidx.biometric rejects the pair, so those releases fall back to the
     * biometric alone and offer signing out as the way past the lock.
     */
    private fun unlockAuthenticators(): Int =
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.R) {
            BiometricManager.Authenticators.BIOMETRIC_STRONG or
                BiometricManager.Authenticators.DEVICE_CREDENTIAL
        } else {
            BiometricManager.Authenticators.BIOMETRIC_STRONG
        }

    /** True when this device can satisfy an unlock prompt at all. */
    fun canUnlock(): Boolean =
        biometricManager.canAuthenticate(unlockAuthenticators()) ==
            BiometricManager.BIOMETRIC_SUCCESS

    /**
     * The unlock prompt for the idle lock.
     *
     * Deliberately not bound to a CryptoObject. The only key this app holds is
     * the biometric *login* signing key, which is single-use, exists only for
     * accounts that enrolled, and is destroyed when the device's fingerprints
     * change — spending it here would break login for the sake of a screen that
     * is already gated by the OS. So this call proves the OS was satisfied and
     * nothing more, which is exactly what re-covering a live session requires;
     * the session's own tokens remain protected by the Keystore-backed
     * preferences either way.
     *
     * [onFailure] covers every ending that is not a success, cancellation
     * included: a lock that opens because the user dismissed the prompt is not a
     * lock. The caller keeps the screen covered and leaves signing out as the
     * only other way forward.
     */
    fun authenticateToUnlock(
        activity: FragmentActivity,
        onSuccess: () -> Unit,
        onFailure: (String?) -> Unit
    ) {
        val authenticators = unlockAuthenticators()
        val promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle("التطبيق مقفل")
            .setSubtitle("أكّد هويتك لمتابعة الجلسة")
            .setAllowedAuthenticators(authenticators)
            .setConfirmationRequired(false)
            .apply {
                // A negative button is rejected when DEVICE_CREDENTIAL is
                // allowed — the system supplies its own "use PIN" affordance.
                if (authenticators and BiometricManager.Authenticators.DEVICE_CREDENTIAL == 0) {
                    setNegativeButtonText("إلغاء")
                }
            }
            .build()

        val prompt = BiometricPrompt(activity, executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    onSuccess()
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    when (errorCode) {
                        BiometricPrompt.ERROR_USER_CANCELED,
                        BiometricPrompt.ERROR_NEGATIVE_BUTTON,
                        BiometricPrompt.ERROR_CANCELED -> onFailure(null)
                        else -> onFailure(errString.toString())
                    }
                }
            }
        )
        prompt.authenticate(promptInfo)
    }
}
