package com.securemed.app.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.data.model.Channel
import com.securemed.app.data.model.ChatMessage
import com.securemed.app.data.model.ChannelMembership
import com.securemed.app.data.model.MedicalRecord
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class ChannelsViewModel : ViewModel() {
    private val repository = SecureMedRepository()

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

class ChannelDetailViewModel : ViewModel() {
    private val repository = SecureMedRepository()

    data class ChannelDetailState(
        val isLoading: Boolean = true,
        val channel: Channel? = null,
        val members: List<ChannelMembership> = emptyList(),
        val records: List<MedicalRecord> = emptyList(),
        val messages: List<ChatMessage> = emptyList(),
        val isSending: Boolean = false,
        val error: String? = null
    )

    private val _state = MutableStateFlow(ChannelDetailState())
    val state: StateFlow<ChannelDetailState> = _state

    /** ID of the currently logged-in user — marks "my" chat bubbles. */
    val currentUserId: String? = SecurePreferences.userId

    private var channelId: String = ""
    private var pollJob: Job? = null

    fun loadChannel(id: String) {
        channelId = id
        _state.value = _state.value.copy(isLoading = true)
        viewModelScope.launch {
            val channelResult = repository.getChannel(id)
            val membersResult = repository.getChannelMembers(id)
            val recordsResult = repository.getMedicalRecords(id)
            val messagesResult = repository.getMessages(id)

            _state.value = ChannelDetailState(
                isLoading = false,
                channel = channelResult.getOrNull(),
                members = membersResult.getOrDefault(emptyList()),
                records = recordsResult.getOrDefault(emptyList()),
                messages = messagesResult.getOrDefault(emptyList()),
                error = if (channelResult.isFailure) "فشل تحميل القناة" else null
            )

            startPolling()
        }
    }

    /** Poll for new chat messages every 3 seconds while the screen is open. */
    private fun startPolling() {
        pollJob?.cancel()
        pollJob = viewModelScope.launch {
            while (true) {
                delay(3000)
                if (channelId.isBlank()) continue
                // Incremental fetch: only messages newer than the latest one
                val last = _state.value.messages.lastOrNull()?.createdAt
                runCatching {
                    val fresh = repository.getMessages(channelId).getOrDefault(emptyList())
                    val existing = _state.value.messages
                    if (fresh.size != existing.size ||
                        fresh.lastOrNull()?.id != existing.lastOrNull()?.id
                    ) {
                        _state.value = _state.value.copy(messages = fresh)
                    }
                    last
                }
            }
        }
    }

    fun sendMessage(body: String) {
        val text = body.trim()
        if (text.isEmpty() || channelId.isBlank()) return
        _state.value = _state.value.copy(isSending = true)
        viewModelScope.launch {
            repository.sendMessage(channelId, text)
                .onSuccess { message ->
                    _state.value = _state.value.copy(
                        isSending = false,
                        messages = _state.value.messages + message
                    )
                }
                .onFailure { error ->
                    _state.value = _state.value.copy(
                        isSending = false,
                        error = error.message ?: "فشل إرسال الرسالة"
                    )
                }
        }
    }

    fun clearTransientError() {
        _state.value = _state.value.copy(error = null)
    }

    override fun onCleared() {
        pollJob?.cancel()
        super.onCleared()
    }
}
