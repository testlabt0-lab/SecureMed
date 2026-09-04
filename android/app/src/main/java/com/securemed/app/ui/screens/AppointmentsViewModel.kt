package com.securemed.app.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.model.Appointment
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AppointmentsViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<AppointmentsUiState>(AppointmentsUiState.Loading)
    val uiState: StateFlow<AppointmentsUiState> = _uiState

    init {
        loadAppointments()
    }

    fun loadAppointments() {
        viewModelScope.launch {
            _uiState.value = AppointmentsUiState.Loading
            try {
                val result = repository.getAppointments()
                if (result.isSuccess) {
                    _uiState.value = AppointmentsUiState.Success(result.getOrNull() ?: emptyList())
                } else {
                    _uiState.value = AppointmentsUiState.Error(
                        result.exceptionOrNull()?.message ?: "حدث خطأ أثناء جلب المواعيد"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = AppointmentsUiState.Error(e.localizedMessage ?: "حدث خطأ غير معروف")
            }
        }
    }
}

sealed class AppointmentsUiState {
    object Loading : AppointmentsUiState()
    data class Success(val appointments: List<Appointment>) : AppointmentsUiState()
    data class Error(val message: String) : AppointmentsUiState()
}
