package com.securemed.app.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.api.ApiErrors
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DeleteAccountUiState(
    val inProgress: Boolean = false,
    val message: String? = null,
    /** True when the account is gone and the caller must navigate to login. */
    val deleted: Boolean = false
)

/**
 * Self-service account deletion (Play requirement, 4-3 §2). The server
 * re-verifies the password, deactivates the user, and ends every session;
 * on success the repository runs the full local wipe — alarms, Room, tokens,
 * cache — exactly like a logout, because a wiped account is a signed-out
 * device by definition.
 */
@HiltViewModel
class DeleteAccountViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(DeleteAccountUiState())
    val uiState: StateFlow<DeleteAccountUiState> = _uiState

    fun deleteAccount(password: String) {
        viewModelScope.launch {
            _uiState.value = DeleteAccountUiState(inProgress = true)
            val result = repository.deleteAccount(password)
            if (result.isSuccess) {
                _uiState.value = DeleteAccountUiState(deleted = true)
            } else {
                _uiState.value = _uiState.value.copy(
                    inProgress = false,
                    message = result.exceptionOrNull()
                        ?.let { ApiErrors.messageFor(it, "تعذر حذف الحساب — تحقق من كلمة المرور والاتصال") }
                        ?: "تعذر حذف الحساب — تحقق من كلمة المرور والاتصال"
                )
            }
        }
    }

    fun clearMessage() {
        _uiState.value = _uiState.value.copy(message = null)
    }
}
