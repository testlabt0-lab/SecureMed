package com.securemed.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.api.TwoFactorExpiredException
import com.securemed.app.data.model.BiometricChallengeResponse
import com.securemed.app.data.model.LoginResponse
import com.securemed.app.security.AppLock
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * AuthViewModel - manages authentication state.
 *
 * Dependencies are injected by Hilt instead of being created internally,
 * making this ViewModel fully testable with fake implementations.
 */
@HiltViewModel
class AuthViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<AuthUiState>(AuthUiState.Idle)
    val uiState: StateFlow<AuthUiState> = _uiState

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage

    fun login(email: String, password: String) {
        _uiState.value = AuthUiState.Loading
        viewModelScope.launch {
            repository.login(email, password)
                .onSuccess { response ->
                    when {
                        response.isAuthenticated ->
                            _uiState.value = AuthUiState.Success(response)

                        // The server wants a second factor instead of handing
                        // over a session. Hold the short-lived mfa_token in
                        // state and let the UI collect the code; the previous
                        // build stopped here and told the user to finish on the
                        // web, which made every MFA account unusable on mobile.
                        response.requiresTwoFactor && response.mfaToken != null -> {
                            _errorMessage.value = null
                            _uiState.value = AuthUiState.AwaitingTwoFactor(
                                mfaToken = response.mfaToken,
                                method = response.method
                            )
                        }

                        // requires_2fa with no token to answer it. Nothing the
                        // client can do, so say so rather than opening a code
                        // screen that can only fail.
                        response.requiresTwoFactor -> {
                            _errorMessage.value = response.detail
                                ?: "طلب الخادم رمز تحقق دون إصدار جلسة تحقق. حاول مرة أخرى."
                            _uiState.value = AuthUiState.Error
                        }

                        else -> {
                            _errorMessage.value = response.detail ?: "استجابة غير متوقعة من الخادم"
                            _uiState.value = AuthUiState.Error
                        }
                    }
                }
                .onFailure { error ->
                    _errorMessage.value = error.message ?: "فشل تسجيل الدخول"
                    _uiState.value = AuthUiState.Error
                }
        }
    }

    /**
     * Posts the typed code to `auth/2fa/login/`.
     *
     * Stays in [AuthUiState.AwaitingTwoFactor] on a wrong code — the server
     * keeps the pending token alive for the rest of the 5 minutes, so the user
     * can simply retype. Only an expired token ends the attempt, because a new
     * one can come from nowhere but a fresh password login.
     *
     * [trustDevice] is forwarded as `trust_device`. It marks this install's
     * fingerprint trusted so adaptive MFA stops mailing a code on every sign-in;
     * it is the user's choice to make, so it is never set on their behalf.
     */
    fun submitTwoFactorCode(code: String, trustDevice: Boolean = false) {
        val awaiting = _uiState.value as? AuthUiState.AwaitingTwoFactor ?: return
        if (awaiting.submitting) return

        val trimmed = code.trim()
        if (trimmed.isEmpty()) {
            _errorMessage.value = "أدخل رمز التحقق"
            return
        }

        _errorMessage.value = null
        _uiState.value = awaiting.copy(submitting = true)
        viewModelScope.launch {
            repository.mfaLogin(awaiting.mfaToken, trimmed, trustDevice)
                .onSuccess { response ->
                    _uiState.value = AuthUiState.Success(response)
                }
                .onFailure { error ->
                    if (error is TwoFactorExpiredException) {
                        expireTwoFactor(error.message)
                    } else {
                        _errorMessage.value = error.message ?: "تعذر التحقق من الرمز"
                        _uiState.value = awaiting.copy(submitting = false)
                    }
                }
        }
    }

    /**
     * The 5-minute window ran out — locally, or as reported by the server.
     *
     * Drops back to the login form rather than leaving a code screen whose
     * token no longer exists, since retrying the code there could only fail.
     */
    fun expireTwoFactor(message: String? = null) {
        _errorMessage.value = message ?: "انتهت مهلة رمز التحقق، سجّل الدخول من جديد"
        _uiState.value = AuthUiState.Error
    }

    /** The user chose to go back instead of entering a code. */
    fun cancelTwoFactor() {
        resetState()
    }

    /**
     * Step one of a biometric login: fetch the challenge and hand it to the UI,
     * which is the only layer that can raise the biometric prompt.
     *
     * A challenge arrives even for an account that never enrolled — the server
     * answers with an indistinguishable decoy on purpose — so reaching
     * [AuthUiState.AwaitingBiometric] proves nothing about the account.
     */
    fun startBiometricLogin(email: String) {
        _uiState.value = AuthUiState.Loading
        viewModelScope.launch {
            repository.getBiometricChallenge(email)
                .onSuccess { challenge ->
                    _uiState.value = AuthUiState.AwaitingBiometric(challenge)
                }
                .onFailure { error ->
                    _errorMessage.value = error.message ?: "تعذر بدء المصادقة البيومترية"
                    _uiState.value = AuthUiState.Error
                }
        }
    }

    /** Step two: send the signature the Keystore produced behind the prompt. */
    fun completeBiometricLogin(challengeId: String, signature: String) {
        _uiState.value = AuthUiState.Loading
        viewModelScope.launch {
            repository.biometricLogin(challengeId, signature)
                .onSuccess { response ->
                    _uiState.value = AuthUiState.Success(response)
                }
                .onFailure { error ->
                    _errorMessage.value = error.message ?: "فشل المصادقة البيومترية"
                    _uiState.value = AuthUiState.Error
                }
        }
    }

    /**
     * Abandon the ceremony without contacting the server — the prompt failed, or
     * this device holds no key. The challenge is simply left to expire.
     */
    fun failBiometric(message: String) {
        _errorMessage.value = message
        _uiState.value = AuthUiState.Error
    }

    fun enrollBiometric(deviceName: String) {
        _uiState.value = AuthUiState.Loading
        viewModelScope.launch {
            repository.enrollBiometric(deviceName)
                .onSuccess {
                    _uiState.value = AuthUiState.BiometricEnrolled
                }
                .onFailure { error ->
                    _errorMessage.value = error.message ?: "فشل تسجيل البصمة"
                    _uiState.value = AuthUiState.Error
                }
        }
    }

    /**
     * Signs out. [allDevices] asks the server to end every session the account
     * holds — the answer to "I lost my phone", and the reason it is offered from
     * settings rather than being what the ordinary logout button does.
     *
     * The local wipe runs either way, so the UI can navigate to the login screen
     * as soon as this returns.
     */
    fun logout(allDevices: Boolean = false) {
        // Synchronous, so the idle lock is lifted in the same frame the caller
        // navigates to the login screen: the overlay must not outlive the session
        // it was covering, and the network call below may take seconds or fail.
        AppLock.reset()
        viewModelScope.launch {
            repository.logout(allDevices)
            _uiState.value = AuthUiState.Idle
        }
    }

    fun resetState() {
        _uiState.value = AuthUiState.Idle
        _errorMessage.value = null
    }
}

sealed class AuthUiState {
    data object Idle : AuthUiState()
    data object Loading : AuthUiState()

    /** A challenge is in hand and the biometric prompt should now be shown. */
    data class AwaitingBiometric(val challenge: BiometricChallengeResponse) : AuthUiState()

    /**
     * The password was accepted but a second factor is outstanding.
     *
     * [method] is the server's choice — "email" for a mailed OTP, "totp" for an
     * authenticator app — and only changes the wording shown to the user; both
     * are answered by the same endpoint. [submitting] lives inside the state
     * instead of switching to [Loading] so the code the user typed stays on
     * screen while it is being checked.
     */
    data class AwaitingTwoFactor(
        val mfaToken: String,
        val method: String?,
        val submitting: Boolean = false
    ) : AuthUiState()

    data class Success(val response: LoginResponse) : AuthUiState()
    data object BiometricEnrolled : AuthUiState()
    data object Error : AuthUiState()
}
