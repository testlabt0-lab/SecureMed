package com.securemed.app.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.api.ApiErrors
import com.securemed.app.data.model.MedicalRecord
import com.securemed.app.data.model.Patient
import com.securemed.app.data.model.PatientFileInfo
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
                // The patient-scoped aggregate (patients/{id}/profile/) returns
                // records of the patient's own channels only — the previous call
                // fetched the global records list and pinned every patient's
                // records under every patient's name (ع6).
                val result = repository.getPatientProfile(patientId)
                val profile = result.getOrNull()
                if (profile != null) {
                    _uiState.value = PatientDetailUiState.Success(
                        patient = profile.patient,
                        records = profile.records,
                        files = profile.files,
                        channels = profile.channels
                    )
                } else {
                    _uiState.value = PatientDetailUiState.Error(
                        result.exceptionOrNull()?.let { ApiErrors.messageFor(it, "حدث خطأ أثناء جلب تفاصيل المريض") }
                            ?: "حدث خطأ أثناء جلب تفاصيل المريض"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = PatientDetailUiState.Error(e.localizedMessage ?: "حدث خطأ غير معروف")
            }
        }
    }

    /**
     * Create a record in one of the patient's channels. Server-side the channel
     * must grant the caller EDITOR-or-higher; a 403 arrives as the server's own
     * Arabic message via [ApiErrors].
     */
    fun createRecord(patientId: String, channelId: String, title: String, content: String, recordType: String, isCritical: Boolean) {
        viewModelScope.launch {
            _uiState.value = (_uiState.value as? PatientDetailUiState.Success)?.copy(
                actionInProgress = true, actionMessage = null
            ) ?: _uiState.value
            val result = repository.createMedicalRecord(
                com.securemed.app.data.model.MedicalRecordCreateRequest(
                    title = title,
                    content = content,
                    recordType = recordType,
                    isCritical = isCritical,
                    channel = channelId
                )
            )
            if (result.isSuccess) {
                // Reload so the new record comes back in the server-attributed list.
                loadPatient(patientId)
                _uiState.value = (_uiState.value as? PatientDetailUiState.Success)?.copy(
                    actionMessage = "تم إنشاء السجل الطبي"
                )
            } else {
                val message = result.exceptionOrNull()?.let { ApiErrors.messageFor(it, "تعذر إنشاء السجل") }
                    ?: "تعذر إنشاء السجل"
                _uiState.value = (_uiState.value as? PatientDetailUiState.Success)?.copy(
                    actionInProgress = false, actionMessage = message
                )
            }
        }
    }

    fun clearActionMessage() {
        _uiState.value = (_uiState.value as? PatientDetailUiState.Success)?.copy(actionMessage = null)
    }
}

sealed class PatientDetailUiState {
    object Loading : PatientDetailUiState()
    data class Success(
        val patient: Patient,
        val records: List<MedicalRecord>,
        val files: List<PatientFileInfo> = emptyList(),
        val channels: List<com.securemed.app.data.model.Channel> = emptyList(),
        val actionInProgress: Boolean = false,
        val actionMessage: String? = null
    ) : PatientDetailUiState()
    data class Error(val message: String) : PatientDetailUiState()
}
