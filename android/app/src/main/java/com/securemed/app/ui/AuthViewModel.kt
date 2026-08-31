package com.securemed.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.model.BiometricChallengeResponse
import com.securemed.app.data.model.LoginResponse
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

/**
 * AuthViewModel - manages authentication state.
 */
class AuthViewModel : ViewModel() {

    private val repository = SecureMedRepository()

    private val _uiState = MutableStateFlow<AuthUiState>(AuthUiState.Idle)
    val uiState: StateFlow<AuthUiState> = _uiState

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage

    fun login(email: String, password: String) {
        _uiState.value = AuthUiState.Loading
        viewModelScope.launch {
            repository.login(email, password)
                .onSuccess { response ->
                    _uiState.value = AuthUiState.Success(response)
                }
                .onFailure { error ->
                    _errorMessage.value = error.message ?: "فشل تسجيل الدخول"
                    _uiState.value = AuthUiState.Error
                }
        }
    }

    /**
     * Step 1 of biometric login: fetch the server challenge for this
     * account + device. The caller then shows the fingerprint prompt and
     * completes with [biometricLogin].
     */
    fun prepareBiometricLogin(email: String) {
        _uiState.value = AuthUiState.Loading
        _errorMessage.value = null
        viewModelScope.launch {
            repository.requestBiometricChallenge(email.trim())
                .onSuccess { challenge ->
                    _uiState.value = AuthUiState.ChallengeReady(challenge)
                }
                .onFailure { error ->
                    _errorMessage.value = error.message
                        ?: "تعذر طلب تحدي البصمة — تأكد من تفعيل البصمة لهذا الحساب"
                    _uiState.value = AuthUiState.Error
                }
        }
    }

    /**
     * Step 2 of biometric login: submit the Keystore signature over the
     * challenge and store the returned session.
     */
    fun biometricLogin(challengeId: String, signatureBase64: String) {
        _uiState.value = AuthUiState.Loading
        viewModelScope.launch {
            repository.biometricLogin(challengeId, signatureBase64)
                .onSuccess { response ->
                    _uiState.value = AuthUiState.Success(response)
                }
                .onFailure { error ->
                    _errorMessage.value = error.message ?: "فشل المصادقة البيومترية"
                    _uiState.value = AuthUiState.Error
                }
        }
    }

    /** Enroll this device's Keystore public key for biometric login. */
    fun enrollBiometric(deviceName: String, publicKeyBase64: String) {
        _uiState.value = AuthUiState.Loading
        viewModelScope.launch {
            repository.enrollBiometric(deviceName, publicKeyBase64)
                .onSuccess {
                    _uiState.value = AuthUiState.BiometricEnrolled
                }
                .onFailure { error ->
                    _errorMessage.value = error.message ?: "فشل تسجيل البصمة"
                    _uiState.value = AuthUiState.Error
                }
        }
    }

    fun logout() {
        repository.logout()
        _uiState.value = AuthUiState.Idle
    }

    fun resetState() {
        _uiState.value = AuthUiState.Idle
        _errorMessage.value = null
    }
}

sealed class AuthUiState {
    object Idle : AuthUiState()
    object Loading : AuthUiState()
    /** Server challenge received — show the biometric prompt now. */
    data class ChallengeReady(val challenge: BiometricChallengeResponse) : AuthUiState()
    data class Success(val response: LoginResponse) : AuthUiState()
    object BiometricEnrolled : AuthUiState()
    object Error : AuthUiState()
}
