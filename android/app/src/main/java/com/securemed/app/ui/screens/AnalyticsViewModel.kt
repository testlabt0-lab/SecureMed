package com.securemed.app.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.model.DashboardStats
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AnalyticsViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<AnalyticsUiState>(AnalyticsUiState.Loading)
    val uiState: StateFlow<AnalyticsUiState> = _uiState

    init {
        loadStats()
    }

    fun loadStats() {
        viewModelScope.launch {
            _uiState.value = AnalyticsUiState.Loading
            try {
                val statsResult = repository.getDashboardOverview()
                if (statsResult.isSuccess) {
                    _uiState.value = AnalyticsUiState.Success(statsResult.getOrNull()!!)
                } else {
                    _uiState.value = AnalyticsUiState.Error(
                        statsResult.exceptionOrNull()?.message ?: "فشل في جلب الإحصائيات"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = AnalyticsUiState.Error(e.localizedMessage ?: "حدث خطأ غير متوقع")
            }
        }
    }
}

sealed class AnalyticsUiState {
    object Loading : AnalyticsUiState()
    data class Success(val stats: DashboardStats) : AnalyticsUiState()
    data class Error(val message: String) : AnalyticsUiState()
}
