package com.securemed.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.model.Notification
import kotlinx.serialization.Serializable

@Serializable
data class NotificationListResponse(
    val results: List<Notification> = emptyList(),
    val count: Int = 0
)

class NotificationsViewModel : ViewModel() {
    private val repository = SecureMedRepository()

    data class State(
        val isLoading: Boolean = true,
        val notifications: List<Notification> = emptyList(),
        val unreadCount: Int = 0,
        val error: String? = null
    )

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state

    init { loadNotifications() }

    fun loadNotifications() {
        _state.value = _state.value.copy(isLoading = true)
        viewModelScope.launch {
            repository.getNotifications().fold(
                onSuccess = { list ->
                    _state.value = State(
                        isLoading = false,
                        notifications = list,
                        unreadCount = list.count { !it.isRead },
                    )
                },
                onFailure = { e ->
                    _state.value = State(isLoading = false, error = e.message)
                },
            )
        }
    }

    fun markAsRead(id: String) {
        viewModelScope.launch {
            repository.markNotificationRead(id)
            loadNotifications()
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NotificationsScreen(onBack: () -> Unit) {
    val viewModel: NotificationsViewModel = viewModel()
    val state by viewModel.state.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("الإشعارات (${state.unreadCount})") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, "رجوع")
                    }
                },
                actions = {
                    if (state.unreadCount > 0) {
                        IconButton(onClick = { /* Mark all read */ }) {
                            Icon(Icons.Default.DoneAll, "تعليم الكل كمقروء")
                        }
                    }
                }
            )
        }
    ) { padding ->
        if (state.isLoading) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator()
            }
        } else if (state.notifications.isEmpty()) {
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
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(state.notifications) { notification ->
                    NotificationCard(
                        notification = notification,
                        onMarkRead = { viewModel.markAsRead(notification.id) }
                    )
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
