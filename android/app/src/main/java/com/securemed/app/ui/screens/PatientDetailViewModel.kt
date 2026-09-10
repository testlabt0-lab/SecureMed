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

    init {
        // Offline-queue outcomes (dropped poison actions, pending syncs) are
        // posted by SyncWorker; surface them where creates originate so a
        // queued or rejected record is never a silent event.
        viewModelScope.launch {
            com.securemed.app.data.sync.SyncEvents.message.collect { message ->
                if (message != null) {
                    val current = _uiState.value as? PatientDetailUiState.Success
                    if (current != null) {
                        _uiState.value = current.copy(actionMessage = message)
                    }
                }
            }
        }
    }

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
            val current = _uiState.value as? PatientDetailUiState.Success
            if (current != null) {
                _uiState.value = current.copy(
                    actionInProgress = true, actionMessage = null
                )
            }
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
                val after = _uiState.value as? PatientDetailUiState.Success
                if (after != null) {
                    _uiState.value = after.copy(actionMessage = "تم إنشاء السجل الطبي")
                }
            } else {
                val message = result.exceptionOrNull()?.let { ApiErrors.messageFor(it, "تعذر إنشاء السجل") }
                    ?: "تعذر إنشاء السجل"
                val after = _uiState.value as? PatientDetailUiState.Success
                if (after != null) {
                    _uiState.value = after.copy(
                        actionInProgress = false, actionMessage = message
                    )
                }
            }
        }
    }

    fun clearActionMessage() {
        val current = _uiState.value as? PatientDetailUiState.Success
        if (current != null) {
            _uiState.value = current.copy(actionMessage = null)
        }
    }

    /**
     * Update a record. The server applies the same EDITOR-or-higher channel
     * gate as creation; a 403 arrives as its own Arabic message.
     */
    fun updateRecord(patientId: String, recordId: String, title: String, content: String, recordType: String, isCritical: Boolean) {
        viewModelScope.launch {
            beginAction()
            val result = repository.updateMedicalRecord(
                id = recordId,
                title = title,
                content = content,
                recordType = recordType,
                isCritical = isCritical
            )
            finishAction(result, "تم تحديث السجل", "تعذر تعديل السجل", patientId)
        }
    }

    /** Delete a record — a 403 for viewers arrives as the server's message. */
    fun deleteRecord(patientId: String, recordId: String) {
        viewModelScope.launch {
            beginAction()
            val result = repository.deleteMedicalRecord(recordId)
            finishAction(result, "تم حذف السجل", "تعذر حذف السجل", patientId)
        }
    }

    /**
     * Book an appointment for THIS patient (3-1: booking from the patient
     * page). Doctors load best-effort for the picker; the server validates
     * the future time and doctor conflicts and its message surfaces via
     * [ApiErrors].
     */
    fun prepareBookingData(onReady: (List<com.securemed.app.data.model.User>) -> Unit) {
        viewModelScope.launch {
            onReady(repository.getDoctors().getOrDefault(emptyList()))
        }
    }

    fun createAppointment(
        patientId: String,
        doctorId: String,
        appointmentType: String,
        priority: String,
        scheduledAt: String,
        durationMinutes: Int,
        title: String,
        notes: String?
    ) {
        viewModelScope.launch {
            beginAction()
            val result = repository.createAppointment(
                com.securemed.app.data.model.AppointmentCreateRequest(
                    patient = patientId,
                    doctor = doctorId,
                    appointmentType = appointmentType,
                    priority = priority,
                    scheduledAt = scheduledAt,
                    durationMinutes = durationMinutes,
                    title = title,
                    notes = notes?.takeIf { it.isNotBlank() }
                )
            )
            finishAction(result, "تم حجز الموعد", "تعذر حجز الموعد", patientId)
        }
    }

    private fun beginAction() {
        val current = _uiState.value as? PatientDetailUiState.Success
        if (current != null) {
            _uiState.value = current.copy(actionInProgress = true, actionMessage = null)
        }
    }

    /**
     * Success reloads the server-attributed list and shows [successMessage];
     * failure keeps the list untouched and surfaces the server's own message.
     */
    private fun finishAction(result: kotlin.Result<*>, successMessage: String, failureFallback: String, patientId: String) {
        if (result.isSuccess) {
            loadPatient(patientId)
            val after = _uiState.value as? PatientDetailUiState.Success
            if (after != null) {
                _uiState.value = after.copy(actionMessage = successMessage)
            }
        } else {
            val message = result.exceptionOrNull()
                ?.let { ApiErrors.messageFor(it, failureFallback) }
                ?: failureFallback
            val current = _uiState.value as? PatientDetailUiState.Success
            if (current != null) {
                _uiState.value = current.copy(actionInProgress = false, actionMessage = message)
            }
        }
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
