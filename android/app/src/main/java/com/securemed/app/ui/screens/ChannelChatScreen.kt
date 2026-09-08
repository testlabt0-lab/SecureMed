package com.securemed.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.model.ChannelMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * In-channel secure chat screen (roadmap Phase 4, backed by the
 * `channels/{id}/messages/` REST action with incremental `?after=` polling).
 *
 * Polling was chosen over a WebSocket here on purpose: the REST action already
 * enforces membership, is the same code path the web SPA uses, and survives
 * process death and backgrounding without a reconnection layer. The
 * incremental fetch (`after=<iso>`) keeps each poll to new rows only.
 */
@HiltViewModel
class ChannelChatViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    data class ChatState(
        val isLoading: Boolean = true,
        val messages: List<ChannelMessage> = emptyList(),
        val channelName: String = "",
        val draft: String = "",
        val sending: Boolean = false,
        val error: String? = null
    )

    private val _state = MutableStateFlow(ChatState())
    val state: StateFlow<ChatState> = _state

    private var channelId: String = ""

    fun load(channelId: String, channelName: String) {
        this.channelId = channelId
        _state.value = _state.value.copy(channelName = channelName)
        refresh()
    }

    fun refresh() {
        if (channelId.isBlank()) return
        viewModelScope.launch {
            val latest = _state.value.messages.lastOrNull()?.createdAt
            repository.getChannelMessages(channelId, after = latest)
                .onSuccess { fresh ->
                    if (fresh.isNotEmpty()) {
                        val combined = (_state.value.messages + fresh)
                            .distinctBy { it.id }
                            .sortedBy { it.createdAt }
                        _state.value = _state.value.copy(
                            isLoading = false, messages = combined, error = null
                        )
                    } else {
                        _state.value = _state.value.copy(isLoading = false, error = null)
                    }
                }
                .onFailure { e ->
                    // An initial load failing offline is an error; a poll
                    // failing just keeps the last view (the next poll retries).
                    if (_state.value.messages.isEmpty()) {
                        _state.value = _state.value.copy(
                            isLoading = false,
                            error = e.message ?: "تعذر تحميل المحادثة"
                        )
                    }
                }
        }
    }

    fun setDraft(value: String) {
        _state.value = _state.value.copy(draft = value)
    }

    fun send() {
        val body = _state.value.draft.trim()
        if (body.isEmpty() || _state.value.sending) return
        viewModelScope.launch {
            _state.value = _state.value.copy(sending = true)
            repository.sendChannelMessage(channelId, body)
                .onSuccess { message ->
                    _state.value = _state.value.copy(
                        draft = "",
                        sending = false,
                        messages = (_state.value.messages + message)
                            .distinctBy { it.id }
                            .sortedBy { it.createdAt }
                    )
                }
                .onFailure { e ->
                    _state.value = _state.value.copy(
                        sending = false,
                        error = e.message ?: "فشل إرسال الرسالة"
                    )
                }
        }
    }

    fun clearError() {
        _state.value = _state.value.copy(error = null)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChannelChatScreen(
    channelId: String,
    channelName: String,
    onBack: () -> Unit
) {
    val viewModel: ChannelChatViewModel = hiltViewModel()
    val state by viewModel.state.collectAsState()
    val listState = rememberLazyListState()

    LaunchedEffect(channelId) {
        viewModel.load(channelId, channelName)
    }

    // Incremental poll while the screen is composed. The ViewModel guards
    // against a blank channel id, so a recomposition race costs one no-op.
    LaunchedEffect(channelId) {
        while (true) {
            delay(5000)
            viewModel.refresh()
        }
    }

    // Keep the newest message visible when the list grows.
    LaunchedEffect(state.messages.size) {
        if (state.messages.isNotEmpty()) {
            listState.animateScrollToItem(state.messages.lastIndex)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(state.channelName.ifBlank { "محادثة القناة" })
                        Text(
                            "مشفرة وخاضعة لسجل التدقيق",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "رجوع")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            state.error?.let { error ->
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = MaterialTheme.colorScheme.errorContainer
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            error,
                            modifier = Modifier.weight(1f),
                            color = MaterialTheme.colorScheme.onErrorContainer,
                            style = MaterialTheme.typography.bodySmall
                        )
                        TextButton(onClick = { viewModel.clearError() }) { Text("حسناً") }
                    }
                }
            }

            if (state.isLoading) {
                Box(
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    contentAlignment = Alignment.Center
                ) { CircularProgressIndicator() }
            } else if (state.messages.isEmpty()) {
                Box(
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        "لا رسائل بعد — ابدأ النقاش السريري حول هذه الحالة",
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            } else {
                LazyColumn(
                    state = listState,
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    contentPadding = PaddingValues(vertical = 12.dp)
                ) {
                    items(state.messages, key = { it.id }) { message ->
                        ChatBubble(message)
                    }
                }
            }

            // Composer
            Surface(tonalElevation = 3.dp) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(8.dp),
                    verticalAlignment = Alignment.Bottom
                ) {
                    OutlinedTextField(
                        value = state.draft,
                        onValueChange = viewModel::setDraft,
                        modifier = Modifier.weight(1f),
                        placeholder = { Text("اكتب رسالة…") },
                        maxLines = 4,
                        shape = RoundedCornerShape(20.dp)
                    )
                    Spacer(Modifier.width(8.dp))
                    FilledIconButton(
                        onClick = viewModel::send,
                        enabled = state.draft.isNotBlank() && !state.sending
                    ) {
                        Icon(Icons.AutoMirrored.Filled.Send, "إرسال")
                    }
                }
            }
        }
    }
}

@Composable
private fun ChatBubble(message: ChannelMessage) {
    val isSystem = message.isSystem
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 4.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                message.senderName.ifBlank { message.sender },
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.primary
            )
            Text(
                message.senderRoleDisplay,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.outline
            )
        }
        Spacer(Modifier.height(2.dp))
        Surface(
            shape = RoundedCornerShape(
                topStart = 4.dp, topEnd = 16.dp,
                bottomStart = 16.dp, bottomEnd = 16.dp
            ),
            color = if (isSystem) MaterialTheme.colorScheme.surfaceVariant
            else MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.5f)
        ) {
            Text(
                message.body,
                modifier = Modifier
                    .clip(RoundedCornerShape(12.dp))
                    .padding(12.dp),
                style = MaterialTheme.typography.bodyMedium
            )
        }
        Text(
            formatTimestamp(message.createdAt),
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.outline,
            modifier = Modifier.align(Alignment.End)
        )
    }
}

/** Local-friendly HH:mm out of an ISO timestamp, without a timezone dance. */
private fun formatTimestamp(iso: String): String {
    return runCatching {
        val time = iso.substringAfter('T').take(5)
        if (time.isNotEmpty()) time else iso.take(16)
    }.getOrDefault(iso.take(16))
}
