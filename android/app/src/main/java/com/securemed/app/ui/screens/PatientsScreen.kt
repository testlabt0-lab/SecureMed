package com.securemed.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Search
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
import androidx.paging.cachedIn
import androidx.paging.compose.collectAsLazyPagingItems
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.model.Patient
import com.securemed.app.ui.components.PullToRefreshLayout
import com.securemed.app.ui.components.StateLayout
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

@HiltViewModel
class PatientsViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    val patientsPagingFlow = Pager(
        config = PagingConfig(pageSize = 20, enablePlaceholders = false),
        pagingSourceFactory = { repository.getPatientPagingSource() }
    ).flow.cachedIn(viewModelScope)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PatientsScreen(
    onPatientClick: (String) -> Unit = {},
    onBack: () -> Unit
) {
    val viewModel: PatientsViewModel = hiltViewModel()
    val patients = viewModel.patientsPagingFlow.collectAsLazyPagingItems()
    var search by remember { mutableStateOf("") }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("المرضى") },
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
                placeholder = { Text("بحث عن مريض (محلي)...") },
                leadingIcon = { Icon(Icons.Default.Search, null) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(modifier = Modifier.height(12.dp))

            val isLoading = patients.loadState.refresh is androidx.paging.LoadState.Loading
            val isError = patients.loadState.refresh is androidx.paging.LoadState.Error
            val error = (patients.loadState.refresh as? androidx.paging.LoadState.Error)?.error?.message
            val filteredPatients = patients.itemSnapshotList.items.filter { patient ->
                search.isBlank() || patient.fullName.contains(search.trim(), ignoreCase = true)
            }

            StateLayout(
                isLoading = isLoading,
                isError = isError,
                errorMessage = error,
                isEmpty = filteredPatients.isEmpty() && !isLoading && !isError,
                emptyMessage = if (search.isBlank()) "لا يوجد مرضى حالياً" else "لا توجد نتائج مطابقة",
                onRetry = { patients.retry() }
            ) {
                PullToRefreshLayout(
                    isRefreshing = isLoading,
                    onRefresh = { patients.refresh() },
                    modifier = Modifier.fillMaxSize()
                ) {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(
                            items = filteredPatients,
                            key = { patient -> patient.id }
                        ) { patient ->
                            PatientCard(
                                patient = patient,
                                onClick = { onPatientClick(patient.id) }
                            )
                        }
                        if (patients.loadState.append is androidx.paging.LoadState.Loading) {
                            item {
                                Box(
                                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                                    contentAlignment = Alignment.Center
                                ) {
                                    CircularProgressIndicator()
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun PatientCard(patient: Patient, onClick: () -> Unit = {}) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable { onClick() },
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .background(
                        MaterialTheme.colorScheme.secondaryContainer,
                        RoundedCornerShape(50)
                    ),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    Icons.Default.Favorite,
                    null,
                    tint = MaterialTheme.colorScheme.onSecondaryContainer
                )
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = patient.fullName,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = "${patient.age ?: "?"} سنة • ${
                        if (patient.gender == "M") "ذكر" else if (patient.gender == "F") "أنثى" else "أخرى"
                    }",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                patient.bloodType?.let {
                    Text(
                        text = "فصيلة الدم: $it",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                patient.chronicConditions?.let {
                    Surface(
                        shape = RoundedCornerShape(6.dp),
                        color = MaterialTheme.colorScheme.tertiary.copy(alpha = 0.1f)
                    ) {
                        Text(
                            text = "⚠️ $it",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.tertiary,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }
                }
            }
        }
    }
}
