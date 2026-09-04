package com.securemed.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.model.LoginResponse
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
                    _uiState.value = AuthUiState.Success(response)
                }
                .onFailure { error ->
                    _errorMessage.value = error.message ?: "فشل تسجيل الدخول"
                    _uiState.value = AuthUiState.Error
                }
        }
    }

    fun biometricLogin(email: String, biometricTemplate: String) {
        _uiState.value = AuthUiState.Loading
        viewModelScope.launch {
            repository.biometricLogin(email, biometricTemplate)
                .onSuccess { response ->
                    _uiState.value = AuthUiState.Success(response)
                }
                .onFailure { error ->
                    _errorMessage.value = error.message ?: "فشل المصادقة البيومترية"
                    _uiState.value = AuthUiState.Error
                }
        }
    }

    fun enrollBiometric(deviceName: String, biometricTemplate: String) {
        _uiState.value = AuthUiState.Loading
        viewModelScope.launch {
            repository.enrollBiometric(deviceName, biometricTemplate)
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
        viewModelScope.launch {
            repository.logout()
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
    data class Success(val response: LoginResponse) : AuthUiState()
    data object BiometricEnrolled : AuthUiState()
    data object Error : AuthUiState()
}
