package com.securemed.app.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.model.LabTestRequest
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class LabViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<LabUiState>(LabUiState.Loading)
    val uiState: StateFlow<LabUiState> = _uiState

    init {
        loadRequests()
    }

    fun loadRequests() {
        viewModelScope.launch {
            _uiState.value = LabUiState.Loading
            try {
                val result = repository.getLabRequests()
                if (result.isSuccess) {
                    _uiState.value = LabUiState.Success(result.getOrNull() ?: emptyList())
                } else {
                    _uiState.value = LabUiState.Error(
                        result.exceptionOrNull()?.message ?: "حدث خطأ أثناء جلب التحاليل"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = LabUiState.Error(e.localizedMessage ?: "حدث خطأ غير معروف")
            }
        }
    }
}

sealed class LabUiState {
    object Loading : LabUiState()
    data class Success(val requests: List<LabTestRequest>) : LabUiState()
    data class Error(val message: String) : LabUiState()
}
