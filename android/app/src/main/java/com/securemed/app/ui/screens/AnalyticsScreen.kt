package com.securemed.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.securemed.app.data.model.DashboardStats

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AnalyticsScreen(
    onBack: () -> Unit,
    viewModel: AnalyticsViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("التحليلات") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "رجوع")
                    }
                }
            )
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            when (val state = uiState) {
                is AnalyticsUiState.Loading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                is AnalyticsUiState.Error -> {
                    Column(
                        modifier = Modifier.align(Alignment.Center),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(text = state.message, color = MaterialTheme.colorScheme.error)
                        Spacer(modifier = Modifier.height(16.dp))
                        Button(onClick = { viewModel.loadStats() }) {
                            Text("إعادة المحاولة")
                        }
                    }
                }
                is AnalyticsUiState.Success -> {
                    AnalyticsContent(stats = state.stats)
                }
            }
        }
    }
}

@Composable
fun AnalyticsContent(stats: DashboardStats) {
    LazyVerticalGrid(
        columns = GridCells.Fixed(2),
        contentPadding = PaddingValues(16.dp),
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        modifier = Modifier.fillMaxSize()
    ) {
        item {
            StatCard(
                title = "إجمالي المستخدمين",
                value = stats.totalUsers.toString(),
                icon = Icons.Default.Group,
                color = MaterialTheme.colorScheme.primary
            )
        }
        item {
            StatCard(
                title = "المستخدمين النشطين",
                value = stats.activeUsers.toString(),
                icon = Icons.Default.Person,
                color = MaterialTheme.colorScheme.tertiary
            )
        }
        item {
            StatCard(
                title = "إجمالي القنوات",
                value = stats.totalChannels.toString(),
                icon = Icons.Default.ChatBubble,
                color = MaterialTheme.colorScheme.secondary
            )
        }
        item {
            StatCard(
                title = "إجمالي المرضى",
                value = stats.totalPatients.toString(),
                icon = Icons.Default.Favorite,
                color = MaterialTheme.colorScheme.error
            )
        }
        item {
            StatCard(
                title = "سجلات طبية",
                value = stats.totalMedicalRecords.toString(),
                icon = Icons.Default.Description,
                color = MaterialTheme.colorScheme.primary
            )
        }
        item {
            StatCard(
                title = "التنبيهات الأمنية",
                value = stats.securityAlertsToday.toString(),
                icon = Icons.Default.Security,
                color = MaterialTheme.colorScheme.error
            )
        }
        item {
            StatCard(
                title = "هجمات WAF المحظورة",
                value = stats.wafBlocksToday.toString(),
                icon = Icons.Default.Block,
                color = MaterialTheme.colorScheme.errorContainer
            )
        }
        item {
            StatCard(
                title = "الدخول بالبصمة",
                value = stats.biometricLoginsToday.toString(),
                icon = Icons.Default.Fingerprint,
                color = MaterialTheme.colorScheme.primaryContainer
            )
        }
    }
}

@Composable
fun StatCard(
    title: String,
    value: String,
    icon: ImageVector,
    color: androidx.compose.ui.graphics.Color
) {
    Card(
        modifier = Modifier.fillMaxWidth().aspectRatio(1f),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = color,
                modifier = Modifier.size(32.dp)
            )
            Column {
                Text(
                    text = value,
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Text(
                    text = title,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}
