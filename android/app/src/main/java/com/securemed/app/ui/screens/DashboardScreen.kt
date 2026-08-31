package com.securemed.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.data.model.Channel
import com.securemed.app.data.model.Patient

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    onNavigateToChannels: () -> Unit,
    onNavigateToPatients: () -> Unit,
    onNavigateToProfile: () -> Unit,
    onNavigateToNotifications: () -> Unit,
    onNavigateToUsers: () -> Unit,
    onNavigateToMedications: () -> Unit,
    onLogout: () -> Unit
) {
    val viewModel: DashboardViewModel = viewModel()
    val state by viewModel.state.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("SecureMed") },
                actions = {
                    IconButton(onClick = onNavigateToNotifications) {
                        Icon(Icons.Default.Notifications, "الإشعارات")
                    }
                    IconButton(onClick = onLogout) {
                        Icon(Icons.Default.Logout, "تسجيل الخروج")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    actionIconContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item {
                // Welcome card
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(modifier = Modifier.padding(20.dp)) {
                        Text(
                            text = "مرحباً، ${SecurePreferences.userName ?: "👋"}",
                            style = MaterialTheme.typography.headlineMedium,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "إليك نظرة على حالاتك اليوم",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            // Stats
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    StatCard(
                        modifier = Modifier.weight(1f),
                        title = "القنوات",
                        count = state.channels.size,
                        icon = Icons.Default.Folder,
                        color = MaterialTheme.colorScheme.primary,
                        onClick = onNavigateToChannels
                    )
                    StatCard(
                        modifier = Modifier.weight(1f),
                        title = "المرضى",
                        count = state.patients.size,
                        icon = Icons.Default.Person,
                        color = MaterialTheme.colorScheme.secondary,
                        onClick = onNavigateToPatients
                    )
                }
            }
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    StatCard(
                        modifier = Modifier.weight(1f),
                        title = "البصمة",
                        count = if (SecurePreferences.biometricEnabled) 1 else 0,
                        countText = if (SecurePreferences.biometricEnabled) "مفعلة" else "غير مفعلة",
                        icon = Icons.Default.Fingerprint,
                        color = MaterialTheme.colorScheme.tertiary,
                        onClick = onNavigateToProfile
                    )
                    StatCard(
                        modifier = Modifier.weight(1f),
                        title = "الأمان",
                        count = 6,
                        countText = "مفعلة",
                        icon = Icons.Default.Security,
                        color = MaterialTheme.colorScheme.error,
                        onClick = {}
                    )
                }
            }

            // Medications + notifications shortcuts (patient core features)
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    StatCard(
                        modifier = Modifier.weight(1f),
                        title = "الأدوية",
                        count = 0,
                        countText = "التذكيرات",
                        icon = Icons.Default.Medication,
                        color = MaterialTheme.colorScheme.secondary,
                        onClick = onNavigateToMedications
                    )
                    StatCard(
                        modifier = Modifier.weight(1f),
                        title = "الإشعارات",
                        count = 0,
                        countText = "المركز",
                        icon = Icons.Default.Notifications,
                        color = MaterialTheme.colorScheme.tertiary,
                        onClick = onNavigateToNotifications
                    )
                }
            }

            // Admin-only: user management shortcut
            if (SecurePreferences.userRole in listOf("SUPER_ADMIN", "HOSPITAL_ADMIN")) {
                item {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        StatCard(
                            modifier = Modifier.weight(1f),
                            title = "المستخدمون",
                            count = 0,
                            countText = "إدارة",
                            icon = Icons.Default.ManageAccounts,
                            color = MaterialTheme.colorScheme.primary,
                            onClick = onNavigateToUsers
                        )
                        Spacer(modifier = Modifier.weight(1f))
                    }
                }
            }

            // Recent channels
            item {
                Text(
                    text = "آخر القنوات",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(vertical = 8.dp)
                )
            }

            if (state.channels.isEmpty() && state.isLoading) {
                item {
                    Box(
                        modifier = Modifier.fillMaxWidth().padding(32.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator()
                    }
                }
            } else {
                items(state.channels.take(5)) { channel ->
                    ChannelCard(
                        channel = channel,
                        onClick = onNavigateToChannels
                    )
                }
            }

            // Security info
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.3f)
                    )
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Security, null, tint = MaterialTheme.colorScheme.primary)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                "مميزات الأمان المفعلة",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        listOf(
                            "وسم الكوكيز الآمنة (HttpOnly, Secure, SameSite)",
                            "ماسح المنافذ المدمج",
                            "JWT مع RS256 + AES-256",
                            "فاحص ثغرات OWASP",
                            "حماية قاعدة البيانات (WAF)",
                            "تشفير TLS 1.3 + DV↔DB"
                        ).forEach { feature ->
                            Text(
                                text = "✓ $feature",
                                style = MaterialTheme.typography.bodySmall,
                                modifier = Modifier.padding(vertical = 2.dp)
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun StatCard(
    modifier: Modifier = Modifier,
    title: String,
    count: Int,
    countText: String? = null,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    color: androidx.compose.ui.graphics.Color,
    onClick: () -> Unit
) {
    Card(
        modifier = modifier
            .height(110.dp)
            .clickable { onClick() },
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            Box(
                modifier = Modifier
                    .size(32.dp)
                    .background(color.copy(alpha = 0.1f), RoundedCornerShape(8.dp)),
                contentAlignment = Alignment.Center
            ) {
                Icon(icon, null, tint = color, modifier = Modifier.size(18.dp))
            }
            Text(
                text = countText ?: count.toString(),
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = title,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun ChannelCard(channel: Channel, onClick: () -> Unit) {
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
                modifier = Modifier
                    .size(8.dp)
                    .background(
                        if (channel.status == "ACTIVE") MaterialTheme.colorScheme.secondary
                        else MaterialTheme.colorScheme.outline,
                        RoundedCornerShape(50)
                    )
            )
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = channel.name,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = channel.channelTypeDisplay,
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

