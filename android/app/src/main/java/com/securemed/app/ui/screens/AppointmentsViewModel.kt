package com.securemed.app.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.cachedIn
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.api.ApiErrors
import com.securemed.app.data.model.Appointment
import com.securemed.app.data.model.Patient
import com.securemed.app.data.model.User
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AppointmentsUiState(
    val actionInProgress: Boolean = false,
    val message: String? = null,
    val isError: Boolean = false
)

@HiltViewModel
class AppointmentsViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(AppointmentsUiState())
    val uiState: StateFlow<AppointmentsUiState> = _uiState

    /**
     * The list itself is paged (3-3); reads happen through
     * [appointmentsPagingFlow] and the Pager follows the server envelope.
     * Write operations that change the list emit here and the screen calls
     * `refresh()` on its LazyPagingItems.
     */
    val appointmentsPagingFlow = Pager(
        config = PagingConfig(pageSize = 20, enablePlaceholders = false),
        pagingSourceFactory = { repository.getAppointmentsPagingSource() }
    ).flow.cachedIn(viewModelScope)

    private val _refreshRequests = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    val refreshRequests: SharedFlow<Unit> = _refreshRequests

    private var loadedPatients: List<Patient> = emptyList()
    private var loadedDoctors: List<User> = emptyList()

    /** Prefetch the lists the booking dialog needs (best-effort). */
    fun prepareBookingData(onReady: (List<Patient>, List<User>) -> Unit) {
        viewModelScope.launch {
            if (loadedPatients.isEmpty()) {
                loadedPatients = repository.getPatients().getOrDefault(emptyList())
            }
            if (loadedDoctors.isEmpty()) {
                loadedDoctors = repository.getDoctors().getOrDefault(emptyList())
            }
            onReady(loadedPatients, loadedDoctors)
        }
    }

    /**
     * Book an appointment. The server validates the future time, doctor
     * conflicts and caller permissions — its message comes back through
     * [ApiErrors] (400 past time/conflict, 403 role).
     */
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
            _uiState.value = _uiState.value.copy(actionInProgress = true, message = null, isError = false)
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
            if (result.isSuccess) {
                requestRefresh()
                _uiState.value = _uiState.value.copy(
                    actionInProgress = false,
                    message = "تم حجز الموعد بنجاح"
                )
            } else {
                _uiState.value = _uiState.value.copy(
                    actionInProgress = false,
                    message = result.exceptionOrNull()
                        ?.let { ApiErrors.messageFor(it, "تعذر حجز الموعد") }
                        ?: "تعذر حجز الموعد",
                    isError = true
                )
            }
        }
    }

    fun cancelAppointment(appointmentId: String, reason: String?) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(actionInProgress = true, message = null, isError = false)
            val result = repository.cancelAppointment(appointmentId, reason)
            if (result.isSuccess) {
                requestRefresh()
                _uiState.value = _uiState.value.copy(
                    actionInProgress = false,
                    message = "تم إلغاء الموعد"
                )
            } else {
                _uiState.value = _uiState.value.copy(
                    actionInProgress = false,
                    message = result.exceptionOrNull()
                        ?.let { ApiErrors.messageFor(it, "تعذر إلغاء الموعد") }
                        ?: "تعذر إلغاء الموعد",
                    isError = true
                )
            }
        }
    }

    private fun requestRefresh() {
        _refreshRequests.tryEmit(Unit)
    }

    fun clearMessage() {
        _uiState.value = _uiState.value.copy(message = null)
    }
}
