package com.securemed.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.securemed.app.data.model.Channel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChannelsScreen(
    onChannelClick: (String) -> Unit,
    onBack: () -> Unit
) {
    val viewModel: ChannelsViewModel = hiltViewModel()
    val state by viewModel.state.collectAsState()
    var search by remember { mutableStateOf("") }

    val filteredChannels = state.channels.filter {
        it.name.contains(search, ignoreCase = true) ||
        it.channelTypeDisplay.contains(search, ignoreCase = true)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("القنوات والحالات") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, "رجوع")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
        ) {
            OutlinedTextField(
                value = search,
                onValueChange = { search = it },
                placeholder = { Text("بحث في القنوات...") },
                leadingIcon = { Icon(Icons.Default.Search, null) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(modifier = Modifier.height(12.dp))

            if (state.isLoading) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            } else if (filteredChannels.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(Icons.Default.Folder, null, modifier = Modifier.size(48.dp),
                             tint = MaterialTheme.colorScheme.outline)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("لا توجد قنوات", color = MaterialTheme.colorScheme.outline)
                    }
                }
            } else {
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(filteredChannels) { channel ->
                        ChannelListItem(
                            channel = channel,
                            onClick = { onChannelClick(channel.id) }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ChannelListItem(channel: Channel, onClick: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier.size(10.dp),
                contentAlignment = Alignment.Center
            ) {
                Box(
                    modifier = Modifier
                        .size(10.dp)
                        .background(
                            if (channel.status == "ACTIVE") MaterialTheme.colorScheme.secondary
                            else MaterialTheme.colorScheme.outline,
                            RoundedCornerShape(50)
                        )
                )
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = channel.name,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = "${channel.channelTypeDisplay} • ${channel.membersCount} أعضاء",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = when (channel.priority) {
                    "URGENT" -> MaterialTheme.colorScheme.error.copy(alpha = 0.1f)
                    "HIGH" -> MaterialTheme.colorScheme.tertiary.copy(alpha = 0.1f)
                    else -> MaterialTheme.colorScheme.primary.copy(alpha = 0.1f)
                }
            ) {
                Text(
                    text = channel.priority,
                    style = MaterialTheme.typography.labelSmall,
                    color = when (channel.priority) {
                        "URGENT" -> MaterialTheme.colorScheme.error
                        "HIGH" -> MaterialTheme.colorScheme.tertiary
                        else -> MaterialTheme.colorScheme.primary
                    },
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                )
            }
        }
    }
}
