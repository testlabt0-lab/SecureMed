package com.securemed.app.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.model.Prescription
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class PharmacyViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<PharmacyUiState>(PharmacyUiState.Loading)
    val uiState: StateFlow<PharmacyUiState> = _uiState

    init {
        loadPrescriptions()
    }

    fun loadPrescriptions() {
        viewModelScope.launch {
            _uiState.value = PharmacyUiState.Loading
            try {
                val result = repository.getPrescriptions()
                if (result.isSuccess) {
                    _uiState.value = PharmacyUiState.Success(result.getOrNull() ?: emptyList())
                } else {
                    _uiState.value = PharmacyUiState.Error(
                        result.exceptionOrNull()?.message ?: "حدث خطأ أثناء جلب الوصفات"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = PharmacyUiState.Error(e.localizedMessage ?: "حدث خطأ غير معروف")
            }
        }
    }

    fun dispensePrescription(id: String) {
        viewModelScope.launch {
            try {
                val result = repository.dispensePrescription(id)
                if (result.isSuccess) {
                    loadPrescriptions() // reload list
                }
            } catch (e: Exception) {
                // Handle error
            }
        }
    }
}

sealed class PharmacyUiState {
    object Loading : PharmacyUiState()
    data class Success(val prescriptions: List<Prescription>) : PharmacyUiState()
    data class Error(val message: String) : PharmacyUiState()
}
