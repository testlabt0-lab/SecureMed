package com.securemed.app.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.model.Channel
import com.securemed.app.data.model.Patient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class DashboardViewModel : ViewModel() {
    private val repository = SecureMedRepository()

    data class DashboardState(
        val isLoading: Boolean = true,
        val channels: List<Channel> = emptyList(),
        val patients: List<Patient> = emptyList(),
        val error: String? = null
    )

    private val _state = MutableStateFlow(DashboardState())
    val state: StateFlow<DashboardState> = _state

    init {
        loadDashboard()
    }

    fun loadDashboard() {
        _state.value = _state.value.copy(isLoading = true, error = null)
        viewModelScope.launch {
            val channelsResult = repository.getChannels()
            val patientsResult = repository.getPatients()

            _state.value = DashboardState(
                isLoading = false,
                channels = channelsResult.getOrDefault(emptyList()),
                patients = patientsResult.getOrDefault(emptyList()),
                error = if (channelsResult.isFailure && patientsResult.isFailure) "فشل تحميل البيانات" else null
            )
        }
    }
}
