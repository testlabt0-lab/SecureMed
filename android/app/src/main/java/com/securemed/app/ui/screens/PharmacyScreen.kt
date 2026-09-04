package com.securemed.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.LocalPharmacy
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.securemed.app.data.model.Prescription

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PharmacyScreen(
    onBack: () -> Unit,
    viewModel: PharmacyViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("الصيدلية") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "رجوع")
                    }
                }
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(16.dp)
        ) {
            OutlinedTextField(
                value = "",
                onValueChange = {},
                placeholder = { Text("ابحث عن وصفة طبية أو مريض...") },
                leadingIcon = { Icon(Icons.Default.Search, null) },
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = "الوصفات الطبية",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary
            )
            Spacer(modifier = Modifier.height(8.dp))
            
            when (val state = uiState) {
                is PharmacyUiState.Loading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.CenterHorizontally))
                }
                is PharmacyUiState.Error -> {
                    Text("خطأ: ${state.message}", color = MaterialTheme.colorScheme.error)
                }
                is PharmacyUiState.Success -> {
                    if (state.prescriptions.isEmpty()) {
                        Text("لا توجد وصفات طبية حالياً.", modifier = Modifier.padding(16.dp))
                    } else {
                        LazyColumn(
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            items(state.prescriptions) { prescription ->
                                PrescriptionCard(prescription = prescription, onDispense = {
                                    viewModel.dispensePrescription(prescription.id)
                                })
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun PrescriptionCard(prescription: Prescription, onDispense: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = Icons.Default.LocalPharmacy,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(32.dp)
            )
            Spacer(modifier = Modifier.width(16.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = prescription.patientName ?: "مريض غير معروف",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )
                val medicines = prescription.items.joinToString(", ") { it.medicationName ?: "دواء غير معروف" }
                Text(
                    text = medicines.ifEmpty { "لا توجد تفاصيل أدوية" },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = "الحالة: ${prescription.status}",
                    style = MaterialTheme.typography.bodySmall,
                    color = if (prescription.status == "ISSUED") MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.secondary
                )
            }
            if (prescription.status == "ISSUED") {
                Button(onClick = onDispense) {
                    Text("صرف")
                }
            }
        }
    }
}
