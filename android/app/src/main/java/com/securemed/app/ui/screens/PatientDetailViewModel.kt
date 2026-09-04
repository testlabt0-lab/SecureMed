package com.securemed.app.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.model.MedicalRecord
import com.securemed.app.data.model.Patient
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class PatientDetailViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<PatientDetailUiState>(PatientDetailUiState.Loading)
    val uiState: StateFlow<PatientDetailUiState> = _uiState

    fun loadPatient(patientId: String) {
        viewModelScope.launch {
            _uiState.value = PatientDetailUiState.Loading
            try {
                val patientResult = repository.getPatient(patientId)
                if (patientResult.isSuccess) {
                    val patient = patientResult.getOrNull()!!
                    
                    // Fetch medical records (simulated or filtered from global records)
                    val recordsResult = repository.getMedicalRecords(null)
                    val records = if (recordsResult.isSuccess) {
                        recordsResult.getOrNull() ?: emptyList()
                    } else {
                        emptyList()
                    }
                    
                    _uiState.value = PatientDetailUiState.Success(patient, records)
                } else {
                    _uiState.value = PatientDetailUiState.Error(
                        patientResult.exceptionOrNull()?.message ?: "حدث خطأ أثناء جلب تفاصيل المريض"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = PatientDetailUiState.Error(e.localizedMessage ?: "حدث خطأ غير معروف")
            }
        }
    }
}

sealed class PatientDetailUiState {
    object Loading : PatientDetailUiState()
    data class Success(val patient: Patient, val records: List<MedicalRecord>) : PatientDetailUiState()
    data class Error(val message: String) : PatientDetailUiState()
}
