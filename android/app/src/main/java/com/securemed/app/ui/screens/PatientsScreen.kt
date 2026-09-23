package com.securemed.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
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
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.flatMapLatest
import android.content.Intent
import android.net.Uri
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.FolderShared
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.ui.platform.LocalContext
import com.securemed.app.hardware.barcode.BarcodeScannerModal
import com.securemed.app.hardware.voice.VoiceInputButton
import com.securemed.app.ui.components.HighlightedText
import com.securemed.app.ui.components.SwipeableActionCard
import javax.inject.Inject

@HiltViewModel
class PatientsViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    /** The live search term, debounced before it becomes a PagingSource. */
    private val _searchTerm = MutableStateFlow("")

    /**
     * Search-driven paging flow. flatMapLatest so typing replaces the in-flight
     * query: without it, every character added a new page source waiting on
     * the same scroll container, and results interleaved.
     *
     * The 350ms debounce keeps "server-side search" from meaning "one request
     * per keystroke" — each pause in typing produces exactly one query.
     */
    @OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
    val patientsPagingFlow = _searchTerm
        .debounce(350)
        .distinctUntilChanged()
        .flatMapLatest { term ->
            Pager(
                config = PagingConfig(pageSize = 20, enablePlaceholders = false),
                pagingSourceFactory = {
                    repository.getPatientPagingSource(
                        search = term.takeIf { it.isNotBlank() }
                    )
                }
            ).flow
        }
        .cachedIn(viewModelScope)

    fun onSearchChanged(term: String) {
        _searchTerm.value = term
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PatientsScreen(
    onPatientClick: (String) -> Unit = {},
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val viewModel: PatientsViewModel = hiltViewModel()
    val patients = viewModel.patientsPagingFlow.collectAsLazyPagingItems()
    var search by remember { mutableStateOf("") }
    var showBarcodeScanner by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("قائمة المرضى") },
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
                .padding(16.dp)
        ) {
            OutlinedTextField(
                value = search,
                onValueChange = {
                    search = it
                    viewModel.onSearchChanged(it)
                },
                placeholder = { Text("بحث فوري بالاسم، الهوية، أو مسح الباركود...") },
                leadingIcon = { Icon(Icons.Default.Search, null) },
                trailingIcon = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        VoiceInputButton { spokenText ->
                            search = spokenText
                            viewModel.onSearchChanged(spokenText)
                        }
                        IconButton(onClick = { showBarcodeScanner = true }) {
                            Icon(
                                Icons.Default.QrCodeScanner,
                                contentDescription = "مسح بطاقة المريض",
                                tint = MaterialTheme.colorScheme.primary
                            )
                        }
                    }
                },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(modifier = Modifier.height(12.dp))

            val isLoading = patients.loadState.refresh is androidx.paging.LoadState.Loading
            val isError = patients.loadState.refresh is androidx.paging.LoadState.Error
            val error = (patients.loadState.refresh as? androidx.paging.LoadState.Error)?.error?.message
            val filteredPatients = patients.itemSnapshotList.items.filter { patient ->
                search.isBlank() || patient.fullName.contains(search.trim(), ignoreCase = true) ||
                    patient.id.contains(search.trim(), ignoreCase = true) ||
                    (patient.phone?.contains(search.trim(), ignoreCase = true) == true)
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
                            SwipeableActionCard(
                                startActionText = "اتصال",
                                startActionIcon = Icons.Default.Call,
                                onStartAction = {
                                    val phone = patient.phone ?: "997"
                                    val dialIntent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:$phone"))
                                    context.startActivity(dialIntent)
                                },
                                endActionText = "فتح الملف",
                                endActionIcon = Icons.Default.FolderShared,
                                onEndAction = { onPatientClick(patient.id) }
                            ) {
                                PatientCard(
                                    patient = patient,
                                    searchQuery = search,
                                    onClick = { onPatientClick(patient.id) }
                                )
                            }
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

        if (showBarcodeScanner) {
            BarcodeScannerModal(
                onDismiss = { showBarcodeScanner = false },
                onBarcodeScanned = { scannedCode ->
                    showBarcodeScanner = false
                    search = scannedCode
                    viewModel.onSearchChanged(scannedCode)
                    // If exact match found, open directly in <0.5s!
                    val exactMatch = patients.itemSnapshotList.items.firstOrNull {
                        it.id == scannedCode || it.phone == scannedCode
                    }
                    if (exactMatch != null) {
                        onPatientClick(exactMatch.id)
                    }
                }
            )
        }
    }
}

@Composable
private fun PatientCard(
    patient: Patient,
    searchQuery: String = "",
    onClick: () -> Unit = {}
) {
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
                HighlightedText(
                    text = patient.fullName,
                    query = searchQuery,
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface
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
