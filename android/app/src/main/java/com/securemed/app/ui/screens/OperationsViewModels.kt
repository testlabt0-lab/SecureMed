package com.securemed.app.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.cachedIn
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.api.ApiErrors
import com.securemed.app.data.model.BedAssignmentCreateRequest
import com.securemed.app.data.model.InvoiceCreateRequest
import com.securemed.app.data.model.InvoiceItemRequest
import com.securemed.app.data.model.LabResultCreateRequest
import com.securemed.app.data.model.Patient
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

/** Write-state shared by the operation screens (progress/message/error). */
data class OperationUiState(
    val actionInProgress: Boolean = false,
    val message: String? = null,
    val isError: Boolean = false
)

/**
 * Lab results (3-6): the read a clinician scans first — abnormal/critical
 * rows are server-computed and rendered with their own colors. Paged like
 * every other list since 3-3. Lab techs can enter new results; the write
 * state is separate from the paged list, and success refreshes it.
 */
@HiltViewModel
class LabResultsViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    val resultsPagingFlow = Pager(
        config = PagingConfig(pageSize = 20, enablePlaceholders = false),
        pagingSourceFactory = { repository.getLabResultsPagingSource() }
    ).flow.cachedIn(viewModelScope)

    private val _uiState = MutableStateFlow(OperationUiState())
    val uiState: StateFlow<OperationUiState> = _uiState

    private val _refreshRequests = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    val refreshRequests: SharedFlow<Unit> = _refreshRequests

    fun createResult(orderId: String, numericValue: Double?, textValue: String?, notes: String?) {
        viewModelScope.launch {
            _uiState.value = OperationUiState(actionInProgress = true)
            val result = repository.createLabResult(
                LabResultCreateRequest(
                    order = orderId,
                    numericValue = numericValue,
                    textValue = textValue?.takeIf { it.isNotBlank() },
                    notes = notes?.takeIf { it.isNotBlank() }
                )
            )
            reportWrite(result, "تم إدخال النتيجة", "تعذر إدخال النتيجة")
        }
    }

    private fun reportWrite(result: kotlin.Result<*>, successMessage: String, failureFallback: String) {
        if (result.isSuccess) {
            _refreshRequests.tryEmit(Unit)
            _uiState.value = _uiState.value.copy(actionInProgress = false, message = successMessage, isError = false)
        } else {
            _uiState.value = _uiState.value.copy(
                actionInProgress = false,
                message = result.exceptionOrNull()
                    ?.let { ApiErrors.messageFor(it, failureFallback) }
                    ?: failureFallback,
                isError = true
            )
        }
    }

    fun clearMessage() {
        _uiState.value = _uiState.value.copy(message = null)
    }
}

/**
 * Wards & beds (3-6): ward cards with occupancy, and a bed map with the
 * admission flow — pick a FREE bed, pick the patient, admit. The server
 * rejects occupied beds and double admissions with its own messages.
 */
@HiltViewModel
class WardsViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    val wardsPagingFlow = Pager(
        config = PagingConfig(pageSize = 20, enablePlaceholders = false),
        pagingSourceFactory = { repository.getWardsPagingSource() }
    ).flow.cachedIn(viewModelScope)

    val bedsPagingFlow = Pager(
        config = PagingConfig(pageSize = 20, enablePlaceholders = false),
        pagingSourceFactory = { repository.getBedsPagingSource(null) }
    ).flow.cachedIn(viewModelScope)

    private val _uiState = MutableStateFlow(OperationUiState())
    val uiState: StateFlow<OperationUiState> = _uiState

    private val _refreshRequests = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    val refreshRequests: SharedFlow<Unit> = _refreshRequests

    private var loadedPatients: List<Patient> = emptyList()

    /** Best-effort patient fetch for the admission dialog. */
    fun prepareAdmissionData(onReady: (List<Patient>) -> Unit) {
        viewModelScope.launch {
            if (loadedPatients.isEmpty()) {
                loadedPatients = repository.getPatients().getOrDefault(emptyList())
            }
            onReady(loadedPatients)
        }
    }

    fun admitPatient(bedId: String, patientId: String, diagnosis: String?) {
        viewModelScope.launch {
            _uiState.value = OperationUiState(actionInProgress = true)
            val result = repository.assignBed(
                BedAssignmentCreateRequest(
                    bed = bedId,
                    patient = patientId,
                    diagnosisOnAdmission = diagnosis?.takeIf { it.isNotBlank() }
                )
            )
            reportWrite(result, "تم إدخال المريض إلى السرير", "تعذر حجز السرير")
        }
    }

    private fun reportWrite(result: kotlin.Result<*>, successMessage: String, failureFallback: String) {
        if (result.isSuccess) {
            _refreshRequests.tryEmit(Unit)
            _uiState.value = _uiState.value.copy(actionInProgress = false, message = successMessage, isError = false)
        } else {
            _uiState.value = _uiState.value.copy(
                actionInProgress = false,
                message = result.exceptionOrNull()
                    ?.let { ApiErrors.messageFor(it, failureFallback) }
                    ?: failureFallback,
                isError = true
            )
        }
    }

    fun clearMessage() {
        _uiState.value = _uiState.value.copy(message = null)
    }
}

/**
 * Invoices (3-6) — the billing status a cashier or admin needs at a glance,
 * plus invoice creation: line items with description/quantity/unit price;
 * totals, VAT and insurance coverage are computed server-side.
 */
@HiltViewModel
class InvoicesViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    val invoicesPagingFlow = Pager(
        config = PagingConfig(pageSize = 20, enablePlaceholders = false),
        pagingSourceFactory = { repository.getInvoicesPagingSource(null) }
    ).flow.cachedIn(viewModelScope)

    private val _uiState = MutableStateFlow(OperationUiState())
    val uiState: StateFlow<OperationUiState> = _uiState

    private val _refreshRequests = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    val refreshRequests: SharedFlow<Unit> = _refreshRequests

    private var loadedPatients: List<Patient> = emptyList()

    fun prepareInvoiceData(onReady: (List<Patient>) -> Unit) {
        viewModelScope.launch {
            if (loadedPatients.isEmpty()) {
                loadedPatients = repository.getPatients().getOrDefault(emptyList())
            }
            onReady(loadedPatients)
        }
    }

    fun createInvoice(patientId: String, discount: Double, dueDate: String?, items: List<InvoiceItemRequest>) {
        viewModelScope.launch {
            _uiState.value = OperationUiState(actionInProgress = true)
            val result = repository.createInvoice(
                InvoiceCreateRequest(
                    patient = patientId,
                    discount = discount,
                    dueDate = dueDate?.takeIf { it.isNotBlank() },
                    items = items
                )
            )
            reportWrite(result, "تم إنشاء الفاتورة", "تعذر إنشاء الفاتورة")
        }
    }

    private fun reportWrite(result: kotlin.Result<*>, successMessage: String, failureFallback: String) {
        if (result.isSuccess) {
            _refreshRequests.tryEmit(Unit)
            _uiState.value = _uiState.value.copy(actionInProgress = false, message = successMessage, isError = false)
        } else {
            _uiState.value = _uiState.value.copy(
                actionInProgress = false,
                message = result.exceptionOrNull()
                    ?.let { ApiErrors.messageFor(it, failureFallback) }
                    ?: failureFallback,
                isError = true
            )
        }
    }

    fun clearMessage() {
        _uiState.value = _uiState.value.copy(message = null)
    }
}

/**
 * Audit trail (3-6) — admin/auditor only (`IsAdmin | IsAuditor` on the
 * server); every other role gets the 403 message rendered as the screen's
 * error state, per the item's acceptance criteria. Read-only by design.
 */
@HiltViewModel
class AuditViewModel @Inject constructor(
    repository: SecureMedRepository
) : ViewModel() {

    val logsPagingFlow = Pager(
        config = PagingConfig(pageSize = 20, enablePlaceholders = false),
        pagingSourceFactory = { repository.getAuditLogsPagingSource(null) }
    ).flow.cachedIn(viewModelScope)
}
