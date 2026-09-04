package com.securemed.app.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.model.Channel
import com.securemed.app.data.model.ChannelMembership
import com.securemed.app.data.model.MedicalRecord
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class ChannelsViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    data class ChannelsState(
        val isLoading: Boolean = true,
        val channels: List<Channel> = emptyList(),
        val error: String? = null
    )

    private val _state = MutableStateFlow(ChannelsState())
    val state: StateFlow<ChannelsState> = _state

    init {
        loadChannels()
    }

    fun loadChannels() {
        _state.value = _state.value.copy(isLoading = true)
        viewModelScope.launch {
            repository.getChannels()
                .onSuccess { channels ->
                    _state.value = ChannelsState(isLoading = false, channels = channels)
                }
                .onFailure { error ->
                    _state.value = ChannelsState(isLoading = false, error = error.message)
                }
        }
    }
}

@HiltViewModel
class ChannelDetailViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    data class ChannelDetailState(
        val isLoading: Boolean = true,
        val channel: Channel? = null,
        val members: List<ChannelMembership> = emptyList(),
        val records: List<MedicalRecord> = emptyList(),
        val error: String? = null
    )

    private val _state = MutableStateFlow(ChannelDetailState())
    val state: StateFlow<ChannelDetailState> = _state

    fun loadChannel(id: String) {
        _state.value = _state.value.copy(isLoading = true)
        viewModelScope.launch {
            val channelResult = repository.getChannel(id)
            val membersResult = repository.getChannelMembers(id)
            val recordsResult = repository.getMedicalRecords(id)

            _state.value = ChannelDetailState(
                isLoading = false,
                channel = channelResult.getOrNull(),
                members = membersResult.getOrDefault(emptyList()),
                records = recordsResult.getOrDefault(emptyList()),
                error = if (channelResult.isFailure) "فشل تحميل القناة" else null
            )
        }
    }
}
