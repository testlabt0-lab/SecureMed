package com.securemed.app.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.api.ApiErrors
import com.securemed.app.data.model.ReportCatalogItem
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.io.File
import javax.inject.Inject

data class ReportsUiState(
    val isLoading: Boolean = true,
    val reports: List<ReportCatalogItem> = emptyList(),
    val errorMessage: String? = null,
    /** The report id currently being downloaded, if any. */
    val downloadingId: String? = null,
    val message: String? = null,
    /** The last successfully downloaded file, for the open action. */
    val downloadedFile: File? = null
)

@HiltViewModel
class ReportsViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(ReportsUiState())
    val uiState: StateFlow<ReportsUiState> = _uiState

    init {
        loadCatalog()
    }

    fun loadCatalog() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
            val result = repository.getReportCatalog()
            if (result.isSuccess) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    reports = result.getOrNull()?.results ?: emptyList()
                )
            } else {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    errorMessage = result.exceptionOrNull()
                        ?.let { ApiErrors.messageFor(it, "تعذر تحميل التقارير") }
                        ?: "تعذر تحميل التقارير"
                )
            }
        }
    }

    /**
     * Download one report. The server enforces the role map and audits the
     * export; a 403 arrives as its own Arabic message. The downloaded file
     * lands in `uiState.downloadedFile` for the open action.
     */
    fun download(report: ReportCatalogItem, format: String, startDate: String?, endDate: String?) {
        if (_uiState.value.downloadingId != null) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                downloadingId = report.id,
                message = null,
                downloadedFile = null
            )
            val result = repository.downloadReport(
                reportId = report.id,
                reportTitle = report.title,
                format = format,
                startDate = startDate?.takeIf { it.isNotBlank() },
                endDate = endDate?.takeIf { it.isNotBlank() }
            )
            val file = result.getOrNull()
            _uiState.value = if (file != null) {
                _uiState.value.copy(
                    downloadingId = null,
                    message = "تم تنزيل التقرير",
                    downloadedFile = file
                )
            } else {
                _uiState.value.copy(
                    downloadingId = null,
                    message = result.exceptionOrNull()
                        ?.let { ApiErrors.messageFor(it, "تعذر تنزيل التقرير") }
                        ?: "تعذر تنزيل التقرير"
                )
            }
        }
    }

    fun clearMessage() {
        _uiState.value = _uiState.value.copy(message = null)
    }
}
