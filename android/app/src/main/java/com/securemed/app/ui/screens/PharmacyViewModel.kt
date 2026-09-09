package com.securemed.app.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.cachedIn
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.api.ApiErrors
import com.securemed.app.data.model.InventoryMedication
import com.securemed.app.data.model.Patient
import com.securemed.app.data.model.Prescription
import com.securemed.app.data.model.PrescriptionCreateRequest
import com.securemed.app.data.model.PrescriptionItemRequest
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class PharmacyUiState(
    val actionInProgress: Boolean = false,
    val message: String? = null,
    val isError: Boolean = false
)

@HiltViewModel
class PharmacyViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(PharmacyUiState())
    val uiState: StateFlow<PharmacyUiState> = _uiState

    /** The prescription list is paged (3-3) — appends as the user scrolls. */
    val prescriptionsPagingFlow = Pager(
        config = PagingConfig(pageSize = 20, enablePlaceholders = false),
        pagingSourceFactory = { repository.getPrescriptionsPagingSource() }
    ).flow.cachedIn(viewModelScope)

    private val _refreshRequests = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    val refreshRequests: SharedFlow<Unit> = _refreshRequests

    private var loadedPatients: List<Patient> = emptyList()
    private var loadedCatalog: List<InventoryMedication> = emptyList()

    /** Best-effort prefetch of the patients and catalog the dialog needs. */
    fun preparePrescriptionData(onReady: (List<Patient>, List<InventoryMedication>) -> Unit) {
        viewModelScope.launch {
            if (loadedPatients.isEmpty()) {
                loadedPatients = repository.getPatients().getOrDefault(emptyList())
            }
            if (loadedCatalog.isEmpty()) {
                loadedCatalog = repository.getMedicationCatalog().getOrDefault(emptyList())
            }
            onReady(loadedPatients, loadedCatalog)
        }
    }

    /**
     * Create a prescription. The server sets the doctor to the caller and
     * rejects unknown medication ids — its message comes back through
     * [ApiErrors].
     */
    fun createPrescription(patientId: String, diagnosisCode: String?, notes: String?, items: List<PrescriptionItemRequest>) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(actionInProgress = true, message = null, isError = false)
            val result = repository.createPrescription(
                PrescriptionCreateRequest(
                    patient = patientId,
                    diagnosisCode = diagnosisCode?.takeIf { it.isNotBlank() },
                    notes = notes?.takeIf { it.isNotBlank() },
                    items = items
                )
            )
            if (result.isSuccess) {
                _refreshRequests.tryEmit(Unit)
                _uiState.value = _uiState.value.copy(
                    actionInProgress = false,
                    message = "تم إنشاء الوصفة الطبية"
                )
            } else {
                _uiState.value = _uiState.value.copy(
                    actionInProgress = false,
                    message = result.exceptionOrNull()
                        ?.let { ApiErrors.messageFor(it, "تعذر إنشاء الوصفة") }
                        ?: "تعذر إنشاء الوصفة",
                    isError = true
                )
            }
        }
    }

    fun dispensePrescription(id: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(actionInProgress = true, message = null, isError = false)
            val result = repository.dispensePrescription(id)
            if (result.isSuccess) {
                _refreshRequests.tryEmit(Unit)
                _uiState.value = _uiState.value.copy(
                    actionInProgress = false,
                    message = "تم صرف الوصفة وخصم المخزون"
                )
            } else {
                _uiState.value = _uiState.value.copy(
                    actionInProgress = false,
                    message = result.exceptionOrNull()
                        ?.let { ApiErrors.messageFor(it, "تعذر صرف الوصفة") }
                        ?: "تعذر صرف الوصفة",
                    isError = true
                )
            }
        }
    }

    fun clearMessage() {
        _uiState.value = _uiState.value.copy(message = null)
    }
}
