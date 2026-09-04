package com.securemed.app.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.local.MedicationStore
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.data.model.Channel
import com.securemed.app.data.model.Patient
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

private val ADMIN_ROLES = listOf("SUPER_ADMIN", "HOSPITAL_ADMIN")

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    data class DashboardState(
        val isLoading: Boolean = true,
        val channels: List<Channel> = emptyList(),
        val patients: List<Patient> = emptyList(),
        val medicationsCount: Int = 0,
        val usersCount: Int = 0,
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

            // Medication plans are device-local; user counts are admin-only.
            val medicationsCount = MedicationStore.loadPlans().count { it.isActive }
            var usersCount = 0
            if (SecurePreferences.userRole in ADMIN_ROLES) {
                repository.getUsers().getOrNull()?.let { usersCount = it.size }
            }

            _state.value = DashboardState(
                isLoading = false,
                channels = channelsResult.getOrDefault(emptyList()),
                patients = patientsResult.getOrDefault(emptyList()),
                medicationsCount = medicationsCount,
                usersCount = usersCount,
                error = if (channelsResult.isFailure && patientsResult.isFailure) "فشل تحميل البيانات" else null
            )
        }
    }
}
