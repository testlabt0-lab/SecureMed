package com.securemed.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.securemed.app.data.model.MedicalRecord
import com.securemed.app.data.model.Patient

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PatientDetailScreen(
    patientId: String,
    onBack: () -> Unit,
    viewModel: PatientDetailViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    LaunchedEffect(patientId) {
        viewModel.loadPatient(patientId)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("تفاصيل المريض") },
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
                is PatientDetailUiState.Loading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                is PatientDetailUiState.Error -> {
                    Column(
                        modifier = Modifier.align(Alignment.Center),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(text = state.message, color = MaterialTheme.colorScheme.error)
                        Spacer(modifier = Modifier.height(16.dp))
                        Button(onClick = { viewModel.loadPatient(patientId) }) {
                            Text("إعادة المحاولة")
                        }
                    }
                }
                is PatientDetailUiState.Success -> {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(16.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        item {
                            PatientProfileCard(patient = state.patient)
                        }
                        
                        item {
                            Text(
                                text = "السجلات الطبية",
                                style = MaterialTheme.typography.titleLarge,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(vertical = 8.dp)
                            )
                        }
                        
                        if (state.records.isEmpty()) {
                            item {
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(32.dp),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Text("لا توجد سجلات طبية لهذا المريض", color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                        } else {
                            items(state.records) { record ->
                                MedicalRecordCard(record = record)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun PatientProfileCard(patient: Patient) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Text(
                text = patient.fullName,
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(8.dp))
            
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(text = "العمر: ${patient.age ?: "غير محدد"}", style = MaterialTheme.typography.bodyMedium)
                Text(text = "الجنس: ${if (patient.gender == "M") "ذكر" else if (patient.gender == "F") "أنثى" else "أخرى"}", style = MaterialTheme.typography.bodyMedium)
            }
            Spacer(modifier = Modifier.height(4.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(text = "فصيلة الدم: ${patient.bloodType ?: "غير محدد"}", style = MaterialTheme.typography.bodyMedium)
                Text(text = "الهاتف: ${patient.phone ?: "غير محدد"}", style = MaterialTheme.typography.bodyMedium)
            }
            
            if (!patient.chronicConditions.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(12.dp))
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = MaterialTheme.colorScheme.errorContainer
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Warning, contentDescription = null, tint = MaterialTheme.colorScheme.onErrorContainer)
                        Spacer(modifier = Modifier.width(8.dp))
                        Column {
                            Text(text = "أمراض مزمنة:", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onErrorContainer)
                            Text(text = patient.chronicConditions, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onErrorContainer)
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun MedicalRecordCard(record: MedicalRecord) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            crossAxisAlignment = CrossAxisAlignment.Start
        ) {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .background(
                        if (record.isCritical) MaterialTheme.colorScheme.errorContainer else MaterialTheme.colorScheme.primaryContainer,
                        shape = RoundedCornerShape(8.dp)
                    ),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    Icons.Default.Description,
                    contentDescription = null,
                    tint = if (record.isCritical) MaterialTheme.colorScheme.onErrorContainer else MaterialTheme.colorScheme.onPrimaryContainer
                )
            }
            Spacer(modifier = Modifier.width(16.dp))
            Column {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = record.title,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = if (record.isCritical) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface
                    )
                    Text(
                        text = record.recordTypeDisplay,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = record.content,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.height(8.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = "بواسطة: ${record.createdByName}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.outline
                    )
                    Text(
                        text = record.createdAt.take(10), // e.g., 2026-09-02
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.outline
                    )
                }
            }
        }
    }
}
