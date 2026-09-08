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
        val error: String? = null,
        // Upload state — a write operation keeps its own progress/error channel
        // so a failed upload never lands in the cached list.
        val uploadInProgress: Boolean = false,
        val uploadMessage: String? = null,
        val uploadIsError: Boolean = false
    )

    private val _state = MutableStateFlow(ChannelDetailState())
    val state: StateFlow<ChannelDetailState> = _state

    fun loadChannel(id: String) {
        _state.value = _state.value.copy(isLoading = true)
        viewModelScope.launch {
            val channelResult = repository.getChannel(id)
            val membersResult = repository.getChannelMembers(id)
            val recordsResult = repository.getMedicalRecords(id)

            _state.value = _state.value.copy(
                isLoading = false,
                channel = channelResult.getOrNull(),
                members = membersResult.getOrDefault(emptyList()),
                records = recordsResult.getOrDefault(emptyList()),
                error = if (channelResult.isFailure) "فشل تحميل القناة" else null
            )
        }
    }

    /**
     * Upload a medical file into this channel. Server-side this needs EDITOR
     * or higher (`perform_create`); 400/403 surface as the server's Arabic
     * message — never a silent failure.
     */
    fun uploadMedicalFile(
        channelId: String,
        patientId: String?,
        fileBytes: ByteArray,
        fileName: String,
        mimeType: String,
        title: String,
        fileType: String,
        description: String?
    ) {
        viewModelScope.launch {
            _state.value = _state.value.copy(uploadInProgress = true, uploadMessage = null, uploadIsError = false)
            val result = repository.uploadMedicalFile(
                fileBytes = fileBytes,
                fileName = fileName,
                mimeType = mimeType,
                channelId = channelId,
                patientId = patientId,
                title = title,
                description = description,
                fileType = fileType
            )
            if (result.isSuccess) {
                _state.value = _state.value.copy(
                    uploadInProgress = false,
                    uploadMessage = "تم رفع الملف بنجاح",
                    uploadIsError = false
                )
            } else {
                _state.value = _state.value.copy(
                    uploadInProgress = false,
                    uploadMessage = result.exceptionOrNull()
                        ?.let { com.securemed.app.data.api.ApiErrors.messageFor(it, "تعذر رفع الملف") }
                        ?: "تعذر رفع الملف",
                    uploadIsError = true
                )
            }
        }
    }

    fun clearUploadMessage() {
        _state.value = _state.value.copy(uploadMessage = null)
    }

    /** A local (pre-server) problem with the picked file — wrong extension, unreadable. */
    fun reportLocalUploadProblem(message: String) {
        _state.value = _state.value.copy(uploadMessage = message, uploadIsError = true)
    }
}
