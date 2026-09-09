package com.securemed.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.LoadState
import androidx.paging.cachedIn
import androidx.paging.compose.collectAsLazyPagingItems
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.api.ApiErrors
import com.securemed.app.data.model.Notification
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.serialization.Serializable
import javax.inject.Inject

@Serializable
data class NotificationListResponse(
    val results: List<Notification> = emptyList(),
    val count: Int = 0
)

@HiltViewModel
class NotificationsViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    data class State(
        val unreadCount: Int = 0,
        val error: String? = null,
        /** After a mark-read/write the paged list refreshes via [refreshRequests]. */
        val actionInProgress: Boolean = false
    )

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state

    /** The list is paged (3-3); loading follows the user's scroll. */
    val notificationsPagingFlow = Pager(
        config = PagingConfig(pageSize = 20, enablePlaceholders = false),
        pagingSourceFactory = { repository.getNotificationsPagingSource() }
    ).flow.cachedIn(viewModelScope)

    private val _refreshRequests = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    val refreshRequests: kotlinx.coroutines.flow.SharedFlow<Unit> = _refreshRequests

    private fun requestRefresh() {
        _refreshRequests.tryEmit(Unit)
    }

    /**
     * The unread badge comes from the lightweight dedicated counter, not from
     * scanning the loaded page — a paged list only holds what has loaded so
     * far, and counting unread rows in it would misstate the total.
     */
    fun loadUnreadCount() {
        viewModelScope.launch {
            repository.getUnreadCount()
                .onSuccess { counts ->
                    _state.value = _state.value.copy(unreadCount = counts["unread_count"] ?: 0)
                }
                .onFailure { e ->
                    _state.value = _state.value.copy(error = e.message)
                }
        }
    }

    fun markAsRead(id: String) {
        viewModelScope.launch {
            _state.value = _state.value.copy(actionInProgress = true)
            repository.markNotificationRead(id)
            loadUnreadCount()
            requestRefresh()
            _state.value = _state.value.copy(actionInProgress = false)
        }
    }

    fun markAllRead() {
        viewModelScope.launch {
            _state.value = _state.value.copy(actionInProgress = true)
            repository.markAllNotificationsRead()
            loadUnreadCount()
            requestRefresh()
            _state.value = _state.value.copy(actionInProgress = false)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NotificationsScreen(onBack: () -> Unit) {
    val viewModel: NotificationsViewModel = hiltViewModel()
    val state by viewModel.state.collectAsState()
    val notifications = viewModel.notificationsPagingFlow.collectAsLazyPagingItems()

    LaunchedEffect(Unit) {
        viewModel.loadUnreadCount()
        viewModel.refreshRequests.collect { notifications.refresh() }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("الإشعارات (${state.unreadCount})") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "رجوع")
                    }
                },
                actions = {
                    if (state.unreadCount > 0) {
                        IconButton(onClick = { viewModel.markAllRead() }) {
                            Icon(Icons.Default.DoneAll, "تعليم الكل كمقروء")
                        }
                    }
                }
            )
        }
    ) { padding ->
        val refreshError = notifications.loadState.refresh as? LoadState.Error
        when {
            notifications.loadState.refresh is LoadState.Loading && notifications.itemCount == 0 -> {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator()
                }
            }
            refreshError != null && notifications.itemCount == 0 -> {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            ApiErrors.messageFor(refreshError.error, "تعذر تحميل الإشعارات"),
                            color = MaterialTheme.colorScheme.error
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        Button(onClick = { notifications.retry() }) { Text("إعادة المحاولة") }
                    }
                }
            }
            notifications.itemCount == 0 -> {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(
                            Icons.Default.Notifications,
                            null,
                            modifier = Modifier.size(48.dp),
                            tint = MaterialTheme.colorScheme.outline
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            "لا توجد إشعارات",
                            color = MaterialTheme.colorScheme.outline
                        )
                    }
                }
            }
            else -> {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding)
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(notifications.itemCount) { index ->
                        notifications[index]?.let { notification ->
                            NotificationCard(
                                notification = notification,
                                onMarkRead = { viewModel.markAsRead(notification.id) }
                            )
                        }
                    }
                    if (notifications.loadState.append is LoadState.Loading) {
                        item {
                            Box(
                                modifier = Modifier.fillMaxWidth().padding(16.dp),
                                contentAlignment = Alignment.Center
                            ) { CircularProgressIndicator() }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun NotificationCard(
    notification: Notification,
    onMarkRead: () -> Unit
) {
    val priorityColor = when (notification.priority) {
        "CRITICAL" -> MaterialTheme.colorScheme.error
        "HIGH" -> MaterialTheme.colorScheme.tertiary
        "MEDIUM" -> MaterialTheme.colorScheme.secondary
        else -> MaterialTheme.colorScheme.primary
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(
            defaultElevation = if (!notification.isRead) 2.dp else 0.dp
        ),
        colors = CardDefaults.cardColors(
            containerColor = if (!notification.isRead)
                MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.3f)
            else MaterialTheme.colorScheme.surface
        )
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(8.dp)
                        .background(priorityColor, RoundedCornerShape(50))
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = notification.title,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = if (!notification.isRead) FontWeight.Bold else FontWeight.SemiBold,
                    modifier = Modifier.weight(1f)
                )
                if (!notification.isRead) {
                    IconButton(
                        onClick = onMarkRead,
                        modifier = Modifier.size(24.dp)
                    ) {
                        Icon(
                            Icons.Default.Check,
                            "تعليم كمقروء",
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }
            }
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = notification.message,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = notification.createdAt,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.outline
            )
        }
    }
}
