package com.securemed.app.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.model.TelemedicineSession
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class TelemedicineViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<TelemedicineUiState>(TelemedicineUiState.Loading)
    val uiState: StateFlow<TelemedicineUiState> = _uiState

    init {
        loadSessions()
    }

    fun loadSessions() {
        viewModelScope.launch {
            _uiState.value = TelemedicineUiState.Loading
            try {
                val result = repository.getTelemedicineSessions()
                if (result.isSuccess) {
                    _uiState.value = TelemedicineUiState.Success(result.getOrNull() ?: emptyList())
                } else {
                    _uiState.value = TelemedicineUiState.Error(
                        result.exceptionOrNull()?.message ?: "حدث خطأ أثناء جلب جلسات التطبيب عن بعد"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = TelemedicineUiState.Error(e.localizedMessage ?: "حدث خطأ غير معروف")
            }
        }
    }
}

sealed class TelemedicineUiState {
    object Loading : TelemedicineUiState()
    data class Success(val sessions: List<TelemedicineSession>) : TelemedicineUiState()
    data class Error(val message: String) : TelemedicineUiState()
}
