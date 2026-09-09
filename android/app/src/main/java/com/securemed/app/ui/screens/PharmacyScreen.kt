package com.securemed.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.LocalPharmacy
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.paging.LoadState
import androidx.paging.compose.collectAsLazyPagingItems
import com.securemed.app.data.api.ApiErrors
import com.securemed.app.data.model.InventoryMedication
import com.securemed.app.data.model.Patient
import com.securemed.app.data.model.Prescription
import com.securemed.app.data.model.PrescriptionItemRequest

/** One editable drug line inside the create-prescription dialog. */
private data class DraftItem(
    val medicationId: String? = null,
    val dosage: String = "",
    val frequency: String = "",
    val durationDays: String = "7",
    val quantity: String = "1"
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PharmacyScreen(
    onBack: () -> Unit,
    viewModel: PharmacyViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    val prescriptions = viewModel.prescriptionsPagingFlow.collectAsLazyPagingItems()
    var showCreateDialog by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        viewModel.refreshRequests.collect { prescriptions.refresh() }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("الصيدلية") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "رجوع")
                    }
                }
            )
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = { viewModel.clearMessage(); showCreateDialog = true },
                icon = { Icon(Icons.Default.Add, contentDescription = null) },
                text = { Text("وصفة جديدة") }
            )
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
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

                val refreshError = prescriptions.loadState.refresh as? LoadState.Error
                when {
                    prescriptions.loadState.refresh is LoadState.Loading && prescriptions.itemCount == 0 -> {
                        Box(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 40.dp),
                            contentAlignment = Alignment.Center
                        ) { CircularProgressIndicator() }
                    }
                    refreshError != null && prescriptions.itemCount == 0 -> {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(
                                ApiErrors.messageFor(refreshError.error, "حدث خطأ أثناء جلب الوصفات"),
                                color = MaterialTheme.colorScheme.error
                            )
                            Spacer(modifier = Modifier.height(12.dp))
                            Button(onClick = { prescriptions.retry() }) { Text("إعادة المحاولة") }
                        }
                    }
                    prescriptions.itemCount == 0 -> {
                        Text("لا توجد وصفات طبية حالياً.", modifier = Modifier.padding(16.dp))
                    }
                    else -> {
                        LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                            items(prescriptions.itemCount) { index ->
                                prescriptions[index]?.let { prescription ->
                                    PrescriptionCard(
                                        prescription = prescription,
                                        onDispense = { viewModel.dispensePrescription(prescription.id) }
                                    )
                                }
                            }
                            if (prescriptions.loadState.append is LoadState.Loading) {
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

            uiState.message?.let { message ->
                Snackbar(
                    modifier = Modifier.align(Alignment.BottomCenter).padding(16.dp),
                    containerColor = if (uiState.isError) MaterialTheme.colorScheme.errorContainer
                    else MaterialTheme.colorScheme.primaryContainer,
                    action = {
                        TextButton(onClick = { viewModel.clearMessage() }) { Text("حسناً") }
                    }
                ) {
                    Text(
                        message,
                        color = if (uiState.isError) MaterialTheme.colorScheme.onErrorContainer
                        else MaterialTheme.colorScheme.onPrimaryContainer
                    )
                }
            }
        }
    }

    if (showCreateDialog) {
        CreatePrescriptionDialog(
            inProgress = uiState.actionInProgress,
            onDismiss = {
                if (!uiState.actionInProgress) {
                    showCreateDialog = false
                    viewModel.clearMessage()
                }
            },
            onLoadOptions = viewModel::preparePrescriptionData,
            onSubmit = { patientId, diagnosisCode, notes, items ->
                viewModel.createPrescription(patientId, diagnosisCode, notes, items)
                showCreateDialog = false
            }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CreatePrescriptionDialog(
    inProgress: Boolean,
    onDismiss: () -> Unit,
    onLoadOptions: ((List<Patient>, List<InventoryMedication>) -> Unit) -> Unit,
    onSubmit: (patientId: String, diagnosisCode: String?, notes: String?, items: List<PrescriptionItemRequest>) -> Unit
) {
    var patients by remember { mutableStateOf<List<Patient>>(emptyList()) }
    var catalog by remember { mutableStateOf<List<InventoryMedication>>(emptyList()) }
    var loaded by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        onLoadOptions { p, c ->
            patients = p
            catalog = c
            loaded = true
        }
    }

    var patientId by remember { mutableStateOf<String?>(null) }
    var patientExpanded by remember { mutableStateOf(false) }
    var diagnosisCode by remember { mutableStateOf("") }
    var notes by remember { mutableStateOf("") }
    var items by remember { mutableStateOf(listOf(DraftItem())) }
    var validationError by remember { mutableStateOf<String?>(null) }

    Dialog(onDismissRequest = onDismiss) {
        Surface(shape = RoundedCornerShape(16.dp), color = MaterialTheme.colorScheme.surface) {
            Column(
                modifier = Modifier
                    .padding(20.dp)
                    .verticalScroll(rememberScrollState())
            ) {
                Text("وصفة طبية جديدة", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(12.dp))

                if (!loaded) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 16.dp),
                        horizontalArrangement = Arrangement.Center
                    ) { CircularProgressIndicator() }
                } else {
                    ExposedDropdownMenuBox(expanded = patientExpanded, onExpandedChange = { patientExpanded = it }) {
                        OutlinedTextField(
                            value = patients.firstOrNull { it.id == patientId }?.fullName ?: "",
                            onValueChange = {},
                            readOnly = true,
                            label = { Text("المريض") },
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(patientExpanded) },
                            modifier = Modifier.menuAnchor().fillMaxWidth()
                        )
                        ExposedDropdownMenu(expanded = patientExpanded, onDismissRequest = { patientExpanded = false }) {
                            patients.forEach { patient ->
                                DropdownMenuItem(
                                    text = { Text(patient.fullName) },
                                    onClick = {
                                        patientId = patient.id
                                        patientExpanded = false
                                    }
                                )
                            }
                        }
                    }
                    Spacer(modifier = Modifier.height(8.dp))

                    OutlinedTextField(
                        value = diagnosisCode,
                        onValueChange = { diagnosisCode = it },
                        label = { Text("رمز التشخيص (اختياري)") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )

                    Spacer(modifier = Modifier.height(12.dp))
                    Text("الأدوية", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)

                    items.forEachIndexed { index, item ->
                        Card(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f)
                            )
                        ) {
                            Column(modifier = Modifier.padding(12.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(
                                        "دواء ${index + 1}",
                                        style = MaterialTheme.typography.labelLarge,
                                        modifier = Modifier.weight(1f)
                                    )
                                    if (items.size > 1) {
                                        IconButton(onClick = { items = items.filterIndexed { i, _ -> i != index } }) {
                                            Icon(
                                                Icons.Default.Delete,
                                                contentDescription = "إزالة",
                                                tint = MaterialTheme.colorScheme.error
                                            )
                                        }
                                    }
                                }

                                var medExpanded by remember(index) { mutableStateOf(false) }
                                ExposedDropdownMenuBox(expanded = medExpanded, onExpandedChange = { medExpanded = it }) {
                                    OutlinedTextField(
                                        value = catalog.firstOrNull { it.id == item.medicationId }?.name ?: "",
                                        onValueChange = {},
                                        readOnly = true,
                                        label = { Text("الدواء (من الفهرس)") },
                                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(medExpanded) },
                                        modifier = Modifier.menuAnchor().fillMaxWidth()
                                    )
                                    ExposedDropdownMenu(expanded = medExpanded, onDismissRequest = { medExpanded = false }) {
                                        catalog.forEach { medication ->
                                            DropdownMenuItem(
                                                text = { Text(medication.name) },
                                                onClick = {
                                                    items = items.mapIndexed { i, draft ->
                                                        if (i == index) draft.copy(medicationId = medication.id) else draft
                                                    }
                                                    medExpanded = false
                                                }
                                            )
                                        }
                                    }
                                }
                                Spacer(modifier = Modifier.height(6.dp))

                                OutlinedTextField(
                                    value = item.dosage,
                                    onValueChange = { value -> items = items.mapIndexed { i, draft -> if (i == index) draft.copy(dosage = value) else draft } },
                                    label = { Text("الجرعة") },
                                    singleLine = true,
                                    modifier = Modifier.fillMaxWidth()
                                )
                                Spacer(modifier = Modifier.height(6.dp))

                                OutlinedTextField(
                                    value = item.frequency,
                                    onValueChange = { value -> items = items.mapIndexed { i, draft -> if (i == index) draft.copy(frequency = value) else draft } },
                                    label = { Text("التكرار") },
                                    singleLine = true,
                                    modifier = Modifier.fillMaxWidth()
                                )
                                Spacer(modifier = Modifier.height(6.dp))

                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    OutlinedTextField(
                                        value = item.durationDays,
                                        onValueChange = { value -> items = items.mapIndexed { i, draft -> if (i == index) draft.copy(durationDays = value.filter { it.isDigit() }.take(3)) else draft } },
                                        label = { Text("المدة (أيام)") },
                                        singleLine = true,
                                        modifier = Modifier.weight(1f)
                                    )
                                    OutlinedTextField(
                                        value = item.quantity,
                                        onValueChange = { value -> items = items.mapIndexed { i, draft -> if (i == index) draft.copy(quantity = value.filter { it.isDigit() }.take(3)) else draft } },
                                        label = { Text("الكمية") },
                                        singleLine = true,
                                        modifier = Modifier.weight(1f)
                                    )
                                }
                            }
                        }
                    }

                    TextButton(onClick = { items = items + DraftItem() }) {
                        Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("إضافة دواء")
                    }

                    Spacer(modifier = Modifier.height(4.dp))
                    OutlinedTextField(
                        value = notes,
                        onValueChange = { notes = it },
                        label = { Text("ملاحظات (اختياري)") },
                        minLines = 2,
                        modifier = Modifier.fillMaxWidth()
                    )

                    if (patients.isEmpty()) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            "لا توجد مرضى متاحون لك",
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                    validationError?.let {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    TextButton(onClick = onDismiss, enabled = !inProgress) { Text("إلغاء") }
                    Spacer(modifier = Modifier.width(8.dp))
                    if (inProgress) {
                        CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
                    } else {
                        Button(
                            onClick = {
                                val parsed = items.mapIndexedNotNull { index, draft ->
                                    val duration = draft.durationDays.toIntOrNull()
                                    val quantity = draft.quantity.toIntOrNull()
                                    when {
                                        draft.medicationId == null -> null.also { validationError = "اختر الدواء في البند ${index + 1}" }
                                        draft.dosage.isBlank() -> null.also { validationError = "أدخل الجرعة في البند ${index + 1}" }
                                        draft.frequency.isBlank() -> null.also { validationError = "أدخل التكرار في البند ${index + 1}" }
                                        duration == null || duration <= 0 -> null.also { validationError = "المدة غير صحيحة في البند ${index + 1}" }
                                        quantity == null || quantity <= 0 -> null.also { validationError = "الكمية غير صحيحة في البند ${index + 1}" }
                                        else -> PrescriptionItemRequest(
                                            medication = draft.medicationId!!,
                                            dosage = draft.dosage.trim(),
                                            frequency = draft.frequency.trim(),
                                            durationDays = duration,
                                            quantity = quantity
                                        )
                                    }
                                }
                                when {
                                    patientId == null -> validationError = "اختر المريض"
                                    parsed.isEmpty() -> if (validationError == null) validationError = "أضف دواءً واحداً على الأقل"
                                    else -> {
                                        validationError = null
                                        onSubmit(patientId!!, diagnosisCode.trim(), notes.trim(), parsed)
                                    }
                                }
                            },
                            enabled = loaded && patients.isNotEmpty() && catalog.isNotEmpty()
                        ) { Text("حفظ الوصفة") }
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
