package com.securemed.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Bed
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Gavel
import androidx.compose.material.icons.filled.Science
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
import androidx.paging.compose.LazyPagingItems
import com.securemed.app.data.api.ApiErrors
import com.securemed.app.data.model.AuditLogEntry
import com.securemed.app.data.model.Bed
import com.securemed.app.data.model.Invoice
import com.securemed.app.data.model.InvoiceItemRequest
import com.securemed.app.data.model.LabResult
import com.securemed.app.data.model.Patient
import com.securemed.app.data.model.Ward

/**
 * Shared skeleton for every paged read-only list (3-6): initial loading,
 * first-page error with the server's message and a retry, the paged items,
 * and an append footer. Keeps the four new screens one pattern.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun <T : Any> PagedListScaffold(
    title: String,
    onBack: () -> Unit,
    items: LazyPagingItems<T>,
    emptyMessage: String,
    floatingActionButton: @Composable () -> Unit = {},
    snackbarHost: @Composable () -> Unit = {},
    itemContent: @Composable (T) -> Unit
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(title) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "رجوع")
                    }
                }
            )
        },
        floatingActionButton = floatingActionButton,
        snackbarHost = { Box { snackbarHost() } }
    ) { padding ->
        PagedListContent(
            items = items,
            emptyMessage = emptyMessage,
            itemContent = itemContent,
            modifier = Modifier.fillMaxSize().padding(padding)
        )
    }
}

/** A write-result banner in the shared operation style (3-6 screens). */
@Composable
internal fun OperationSnackbar(
    message: String?,
    isError: Boolean,
    onDismiss: () -> Unit
) {
    message?.let {
        Snackbar(
            containerColor = if (isError) MaterialTheme.colorScheme.errorContainer
            else MaterialTheme.colorScheme.primaryContainer,
            action = { TextButton(onClick = onDismiss) { Text("حسناً") } }
        ) {
            Text(
                it,
                color = if (isError) MaterialTheme.colorScheme.onErrorContainer
                else MaterialTheme.colorScheme.onPrimaryContainer
            )
        }
    }
}

@Composable
internal fun <T : Any> PagedListContent(
    items: LazyPagingItems<T>,
    emptyMessage: String,
    modifier: Modifier = Modifier,
    itemContent: @Composable (T) -> Unit
) {
    Box(modifier = modifier) {
        val refreshError = items.loadState.refresh as? LoadState.Error
        when {
            items.loadState.refresh is LoadState.Loading && items.itemCount == 0 -> {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
            }
            refreshError != null && items.itemCount == 0 -> {
                Column(
                    modifier = Modifier.align(Alignment.Center).padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        // 403 lands here too — the permission message IS
                        // the screen state for a non-privileged role.
                        ApiErrors.messageFor(refreshError.error, "تعذر تحميل البيانات"),
                        color = MaterialTheme.colorScheme.error
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Button(onClick = { items.retry() }) { Text("إعادة المحاولة") }
                }
            }
            items.itemCount == 0 -> {
                Text(
                    emptyMessage,
                    modifier = Modifier.align(Alignment.Center),
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            else -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(items.itemCount) { index ->
                        items[index]?.let { itemContent(it) }
                    }
                    if (items.loadState.append is LoadState.Loading) {
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LabResultsScreen(onBack: () -> Unit, viewModel: LabResultsViewModel = hiltViewModel()) {
    val results = viewModel.resultsPagingFlow.collectAsLazyPagingItems()
    val uiState by viewModel.uiState.collectAsState()
    var showCreateDialog by remember { mutableStateOf(false) }

    // A newly entered result must appear in the paged list; the Pager caches
    // its flow, so an explicit refresh invalidates the source.
    LaunchedEffect(Unit) {
        viewModel.refreshRequests.collect { results.refresh() }
    }

    PagedListScaffold(
        title = "نتائج المختبر",
        onBack = onBack,
        items = results,
        emptyMessage = "لا توجد نتائج مختبر بعد",
        floatingActionButton = {
            FloatingActionButton(onClick = { viewModel.clearMessage(); showCreateDialog = true }) {
                Icon(Icons.Default.Add, contentDescription = "إدخال نتيجة")
            }
        },
        snackbarHost = {
            OperationSnackbar(uiState.message, uiState.isError) { viewModel.clearMessage() }
        }
    ) { result ->
        LabResultCard(result)
    }

    if (showCreateDialog) {
        CreateLabResultDialog(
            inProgress = uiState.actionInProgress,
            onDismiss = {
                if (!uiState.actionInProgress) {
                    showCreateDialog = false
                    viewModel.clearMessage()
                }
            },
            onSubmit = { orderId, numericText, textValue, notes ->
                // A numeric entry wins when both are filled — the server
                // computes abnormality from the numeric range only.
                val numeric = numericText.trim().replace(',', '.').toDoubleOrNull()
                viewModel.createResult(orderId.trim(), numeric, textValue, notes)
                showCreateDialog = false
            }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CreateLabResultDialog(
    inProgress: Boolean,
    onDismiss: () -> Unit,
    onSubmit: (orderId: String, numericText: String, textValue: String, notes: String) -> Unit
) {
    var orderId by remember { mutableStateOf("") }
    var numericText by remember { mutableStateOf("") }
    var textValue by remember { mutableStateOf("") }
    var notes by remember { mutableStateOf("") }
    var validationError by remember { mutableStateOf<String?>(null) }

    Dialog(onDismissRequest = onDismiss) {
        Surface(shape = RoundedCornerShape(16.dp), color = MaterialTheme.colorScheme.surface) {
            Column(
                modifier = Modifier
                    .padding(20.dp)
                    .verticalScroll(rememberScrollState())
            ) {
                Text("إدخال نتيجة مختبر", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(12.dp))

                OutlinedTextField(
                    value = orderId,
                    onValueChange = { orderId = it },
                    label = { Text("معرّف الطلب (UUID)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))

                OutlinedTextField(
                    value = numericText,
                    onValueChange = { numericText = it },
                    label = { Text("القيمة الرقمية (إن وجدت)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))

                OutlinedTextField(
                    value = textValue,
                    onValueChange = { textValue = it },
                    label = { Text("القيمة النصية (إن وجدت)") },
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))

                OutlinedTextField(
                    value = notes,
                    onValueChange = { notes = it },
                    label = { Text("ملاحظات (اختياري)") },
                    minLines = 2,
                    modifier = Modifier.fillMaxWidth()
                )

                validationError?.let {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                }

                Spacer(modifier = Modifier.height(16.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End, verticalAlignment = Alignment.CenterVertically) {
                    TextButton(onClick = onDismiss, enabled = !inProgress) { Text("إلغاء") }
                    Spacer(modifier = Modifier.width(8.dp))
                    if (inProgress) {
                        CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
                    } else {
                        Button(
                            onClick = {
                                when {
                                    orderId.isBlank() -> validationError = "أدخل معرّف الطلب"
                                    numericText.isBlank() && textValue.isBlank() ->
                                        validationError = "أدخل قيمة رقمية أو نصية على الأقل"
                                    else -> {
                                        validationError = null
                                        onSubmit(orderId, numericText, textValue, notes)
                                    }
                                }
                            }
                        ) { Text("حفظ") }
                    }
                }
            }
        }
    }
}

@Composable
private fun LabResultCard(result: LabResult) {
    val valueText = result.textValue
        ?: result.numericValue?.let { formatDecimal(it) }
        ?: "—"
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (result.isCritical) MaterialTheme.colorScheme.errorContainer
            else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
        )
    ) {
        Row(modifier = Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(
                Icons.Default.Science,
                contentDescription = null,
                tint = if (result.isCritical) MaterialTheme.colorScheme.onErrorContainer
                else MaterialTheme.colorScheme.tertiary,
                modifier = Modifier.size(32.dp)
            )
            Spacer(modifier = Modifier.width(16.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = valueText,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = if (result.isCritical) MaterialTheme.colorScheme.onErrorContainer
                    else MaterialTheme.colorScheme.onSurface
                )
                Text(
                    text = buildString {
                        if (result.isCritical) append("حرج")
                        else if (result.isAbnormal) append("غير طبيعي")
                        else append("طبيعي")
                        result.validatedByName?.let { append(" • مصادق: $it") }
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = if (result.isCritical) MaterialTheme.colorScheme.onErrorContainer
                    else MaterialTheme.colorScheme.onSurfaceVariant
                )
                result.notes?.let {
                    Text(
                        it,
                        style = MaterialTheme.typography.bodySmall,
                        color = if (result.isCritical) MaterialTheme.colorScheme.onErrorContainer
                        else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            if (result.isCritical) {
                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = MaterialTheme.colorScheme.error
                ) {
                    Text(
                        "حرج",
                        color = MaterialTheme.colorScheme.onError,
                        style = MaterialTheme.typography.labelSmall,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                    )
                }
            }
        }
    }
}

private fun formatDecimal(value: Double): String =
    if (value == value.toLong().toDouble()) value.toLong().toString() else value.toString()

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WardsScreen(onBack: () -> Unit, viewModel: WardsViewModel = hiltViewModel()) {
    val wards = viewModel.wardsPagingFlow.collectAsLazyPagingItems()
    val beds = viewModel.bedsPagingFlow.collectAsLazyPagingItems()
    val uiState by viewModel.uiState.collectAsState()
    var showAdmitDialog by remember { mutableStateOf(false) }
    var admittingBed by remember { mutableStateOf<Bed?>(null) }

    // An admission changes bed statuses server-side; refresh both lists.
    LaunchedEffect(Unit) {
        viewModel.refreshRequests.collect {
            beds.refresh()
            wards.refresh()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("الأقسام والأسرّة") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "رجوع")
                    }
                }
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { viewModel.clearMessage(); showAdmitDialog = true }) {
                Icon(Icons.Default.Add, contentDescription = "إدخال مريض لسرير")
            }
        },
        snackbarHost = {
            Box { OperationSnackbar(uiState.message, uiState.isError) { viewModel.clearMessage() } }
        }
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            // Ward occupancy ribbon: the admission question gets answered
            // without opening each ward. The ward table is small by design
            // (tens of rows per basin), so a loaded-page snapshot suffices.
            if (wards.loadState.refresh is LoadState.NotLoading && wards.itemCount > 0) {
                LazyRow(
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(wards.itemCount) { index ->
                        wards[index]?.let { ward ->
                            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)) {
                                Column(modifier = Modifier.padding(12.dp)) {
                                    Text(ward.name, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.SemiBold)
                                    Text(
                                        "الإشغال: ${ward.occupiedBeds}/${ward.totalBeds}",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSecondaryContainer
                                    )
                                }
                            }
                        }
                    }
                }
            }

            PagedListContent(
                items = beds,
                emptyMessage = "لا توجد أسرّة مسجلة",
                modifier = Modifier.weight(1f)
            ) { bed ->
                BedCard(
                    bed = bed,
                    onAdmit = {
                        if (bed.status == "FREE") {
                            viewModel.clearMessage()
                            admittingBed = bed
                        }
                    }
                )
            }
        }
    }

    admittingBed?.let { bed ->
        AdmitPatientDialog(
            bedLabel = "سرير ${bed.bedNumber} — غرفة ${bed.roomNumber}",
            inProgress = uiState.actionInProgress,
            onDismiss = {
                if (!uiState.actionInProgress) {
                    admittingBed = null
                    viewModel.clearMessage()
                }
            },
            onLoadPatients = viewModel::prepareAdmissionData,
            onSubmit = { patientId, diagnosis ->
                viewModel.admitPatient(bed.id, patientId, diagnosis)
                admittingBed = null
            }
        )
    }

    if (showAdmitDialog && admittingBed == null) {
        // Opened from the FAB without a pre-picked bed: reuse the same dialog
        // but let the user pick any bed. Simplest correct flow: close and let
        // the user tap a FREE bed card — admission is always bed-first.
        showAdmitDialog = false
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AdmitPatientDialog(
    bedLabel: String,
    inProgress: Boolean,
    onDismiss: () -> Unit,
    onLoadPatients: ((List<Patient>) -> Unit) -> Unit,
    onSubmit: (patientId: String, diagnosis: String?) -> Unit
) {
    var patients by remember { mutableStateOf<List<Patient>>(emptyList()) }
    var loaded by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        onLoadPatients { patients = it; loaded = true }
    }

    var patientId by remember { mutableStateOf<String?>(null) }
    var patientExpanded by remember { mutableStateOf(false) }
    var diagnosis by remember { mutableStateOf("") }
    var validationError by remember { mutableStateOf<String?>(null) }

    Dialog(onDismissRequest = onDismiss) {
        Surface(shape = RoundedCornerShape(16.dp), color = MaterialTheme.colorScheme.surface) {
            Column(modifier = Modifier.padding(20.dp)) {
                Text("إدخال مريض", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(4.dp))
                Text(bedLabel, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(modifier = Modifier.height(12.dp))

                if (!loaded) {
                    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 16.dp), horizontalArrangement = Arrangement.Center) {
                        CircularProgressIndicator()
                    }
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
                        value = diagnosis,
                        onValueChange = { diagnosis = it },
                        label = { Text("تشخيص الدخول (اختياري)") },
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
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End, verticalAlignment = Alignment.CenterVertically) {
                    TextButton(onClick = onDismiss, enabled = !inProgress) { Text("إلغاء") }
                    Spacer(modifier = Modifier.width(8.dp))
                    if (inProgress) {
                        CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
                    } else {
                        Button(
                            onClick = {
                                if (patientId == null) validationError = "اختر المريض"
                                else {
                                    validationError = null
                                    onSubmit(patientId!!, diagnosis.trim())
                                }
                            },
                            enabled = loaded && patients.isNotEmpty()
                        ) { Text("إدخال") }
                    }
                }
            }
        }
    }
}

@Composable
private fun BedCard(bed: Bed, onAdmit: () -> Unit = {}) {
    val (color, label) = when (bed.status) {
        "FREE" -> MaterialTheme.colorScheme.primary to "متاح"
        "OCCUPIED" -> MaterialTheme.colorScheme.error to "مشغول"
        "MAINTENANCE" -> MaterialTheme.colorScheme.outline to "صيانة"
        "CLEANING" -> MaterialTheme.colorScheme.tertiary to "قيد التنظيف"
        "RESERVED" -> MaterialTheme.colorScheme.secondary to "محجوز"
        else -> MaterialTheme.colorScheme.outline to bed.status
    }
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(modifier = Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.Bed, contentDescription = null, tint = color, modifier = Modifier.size(32.dp))
            Spacer(modifier = Modifier.width(16.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    "سرير ${bed.bedNumber} — غرفة ${bed.roomNumber}",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    bed.wardName,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            if (bed.status == "FREE") {
                TextButton(onClick = onAdmit) { Text("إدخال") }
            } else {
                Surface(shape = RoundedCornerShape(6.dp), color = color.copy(alpha = 0.15f)) {
                    Text(
                        label,
                        color = color,
                        style = MaterialTheme.typography.labelSmall,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun InvoicesScreen(onBack: () -> Unit, viewModel: InvoicesViewModel = hiltViewModel()) {
    val invoices = viewModel.invoicesPagingFlow.collectAsLazyPagingItems()
    val uiState by viewModel.uiState.collectAsState()
    var showCreateDialog by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        viewModel.refreshRequests.collect { invoices.refresh() }
    }

    PagedListScaffold(
        title = "الفواتير",
        onBack = onBack,
        items = invoices,
        emptyMessage = "لا توجد فواتير",
        floatingActionButton = {
            FloatingActionButton(onClick = { viewModel.clearMessage(); showCreateDialog = true }) {
                Icon(Icons.Default.Add, contentDescription = "فاتورة جديدة")
            }
        },
        snackbarHost = {
            OperationSnackbar(uiState.message, uiState.isError) { viewModel.clearMessage() }
        }
    ) { invoice ->
        InvoiceCard(invoice)
    }

    if (showCreateDialog) {
        CreateInvoiceDialog(
            inProgress = uiState.actionInProgress,
            onDismiss = {
                if (!uiState.actionInProgress) {
                    showCreateDialog = false
                    viewModel.clearMessage()
                }
            },
            onLoadPatients = viewModel::prepareInvoiceData,
            onSubmit = { patientId, discountText, dueDate, items ->
                viewModel.createInvoice(
                    patientId,
                    discountText.trim().replace(',', '.').toDoubleOrNull() ?: 0.0,
                    dueDate.trim().takeIf { it.isNotBlank() },
                    items
                )
                showCreateDialog = false
            }
        )
    }
}

/** One editable invoice line inside the create-invoice dialog. */
private data class DraftInvoiceItem(
    val description: String = "",
    val quantity: String = "1",
    val unitPrice: String = ""
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CreateInvoiceDialog(
    inProgress: Boolean,
    onDismiss: () -> Unit,
    onLoadPatients: ((List<Patient>) -> Unit) -> Unit,
    onSubmit: (patientId: String, discountText: String, dueDate: String, items: List<InvoiceItemRequest>) -> Unit
) {
    var patients by remember { mutableStateOf<List<Patient>>(emptyList()) }
    var loaded by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        onLoadPatients { patients = it; loaded = true }
    }

    var patientId by remember { mutableStateOf<String?>(null) }
    var patientExpanded by remember { mutableStateOf(false) }
    var discount by remember { mutableStateOf("0") }
    var dueDate by remember { mutableStateOf("") }
    var items by remember { mutableStateOf(listOf(DraftInvoiceItem())) }
    var validationError by remember { mutableStateOf<String?>(null) }

    Dialog(onDismissRequest = onDismiss) {
        Surface(shape = RoundedCornerShape(16.dp), color = MaterialTheme.colorScheme.surface) {
            Column(
                modifier = Modifier
                    .padding(20.dp)
                    .verticalScroll(rememberScrollState())
            ) {
                Text("فاتورة جديدة", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
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

                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(
                            value = discount,
                            onValueChange = { discount = it.filter { c -> c.isDigit() || c == '.' || c == ',' }.take(8) },
                            label = { Text("الخصم") },
                            singleLine = true,
                            modifier = Modifier.weight(1f)
                        )
                        OutlinedTextField(
                            value = dueDate,
                            onValueChange = { dueDate = it },
                            label = { Text("الاستحقاق (YYYY-MM-DD)") },
                            singleLine = true,
                            modifier = Modifier.weight(1f)
                        )
                    }
                    Spacer(modifier = Modifier.height(12.dp))

                    Text("البنود", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)

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
                                        "بند ${index + 1}",
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
                                OutlinedTextField(
                                    value = item.description,
                                    onValueChange = { value -> items = items.mapIndexed { i, draft -> if (i == index) draft.copy(description = value) else draft } },
                                    label = { Text("الوصف") },
                                    singleLine = true,
                                    modifier = Modifier.fillMaxWidth()
                                )
                                Spacer(modifier = Modifier.height(6.dp))
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    OutlinedTextField(
                                        value = item.quantity,
                                        onValueChange = { value -> items = items.mapIndexed { i, draft -> if (i == index) draft.copy(quantity = value.filter { c -> c.isDigit() }.take(4)) else draft } },
                                        label = { Text("الكمية") },
                                        singleLine = true,
                                        modifier = Modifier.weight(1f)
                                    )
                                    OutlinedTextField(
                                        value = item.unitPrice,
                                        onValueChange = { value -> items = items.mapIndexed { i, draft -> if (i == index) draft.copy(unitPrice = value.filter { c -> c.isDigit() || c == '.' || c == ',' }.take(10)) else draft } },
                                        label = { Text("سعر الوحدة") },
                                        singleLine = true,
                                        modifier = Modifier.weight(1f)
                                    )
                                }
                            }
                        }
                    }

                    TextButton(onClick = { items = items + DraftInvoiceItem() }) {
                        Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("إضافة بند")
                    }

                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        // The same math the server performs — shown live so the
                        // creator sees what will land on the invoice, but the
                        // server's own totals remain authoritative.
                        text = "الإجمالي المرئي: " + formatDecimal(
                            items.sumOf { draft ->
                                (draft.quantity.toIntOrNull() ?: 0) * (draft.unitPrice.replace(',', '.').toDoubleOrNull() ?: 0.0)
                            }
                        ) + " (قبل الخصم والضريبة — النهائي من الخادم)",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
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
                                    val quantity = draft.quantity.toIntOrNull()
                                    val unitPrice = draft.unitPrice.replace(',', '.').toDoubleOrNull()
                                    when {
                                        draft.description.isBlank() -> null.also { validationError = "أدخل وصف البند ${index + 1}" }
                                        quantity == null || quantity <= 0 -> null.also { validationError = "الكمية غير صحيحة في البند ${index + 1}" }
                                        unitPrice == null || unitPrice < 0 -> null.also { validationError = "سعر الوحدة غير صحيح في البند ${index + 1}" }
                                        else -> InvoiceItemRequest(
                                            description = draft.description.trim(),
                                            quantity = quantity,
                                            unitPrice = unitPrice
                                        )
                                    }
                                }
                                when {
                                    patientId == null -> validationError = "اختر المريض"
                                    parsed.isEmpty() -> if (validationError == null) validationError = "أضف بنداً واحداً على الأقل"
                                    else -> {
                                        validationError = null
                                        onSubmit(patientId!!, discount, dueDate, parsed)
                                    }
                                }
                            },
                            enabled = loaded && patients.isNotEmpty()
                        ) { Text("حفظ الفاتورة") }
                    }
                }
            }
        }
    }
}

@Composable
private fun InvoiceCard(invoice: Invoice) {
    val statusLabel = when (invoice.status) {
        "DRAFT" -> "مسودة"
        "PENDING_INSURANCE" -> "بانتظار التأمين"
        "UNPAID" -> "غير مدفوعة"
        "PARTIAL" -> "مدفوعة جزئياً"
        "PAID" -> "مدفوعة"
        "CANCELLED" -> "ملغاة"
        else -> invoice.status
    }
    val statusColor = when (invoice.status) {
        "PAID" -> MaterialTheme.colorScheme.primary
        "UNPAID", "PARTIAL" -> MaterialTheme.colorScheme.error
        else -> MaterialTheme.colorScheme.secondary
    }
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(modifier = Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.Description, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(32.dp))
            Spacer(modifier = Modifier.width(16.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    invoice.patientName ?: "مريض غير معروف",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    "الإجمالي: ${formatDecimal(invoice.finalTotalWithVat)} • المستحق: ${formatDecimal(invoice.patientPayable)}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Surface(shape = RoundedCornerShape(6.dp), color = statusColor.copy(alpha = 0.15f)) {
                Text(
                    statusLabel,
                    color = statusColor,
                    style = MaterialTheme.typography.labelSmall,
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                )
            }
        }
    }
}

@Composable
fun AuditScreen(onBack: () -> Unit, viewModel: AuditViewModel = hiltViewModel()) {
    val logs = viewModel.logsPagingFlow.collectAsLazyPagingItems()
    PagedListScaffold(
        title = "سجل التدقيق",
        onBack = onBack,
        items = logs,
        emptyMessage = "لا توجد أحداث تدقيق"
    ) { entry ->
        AuditLogCard(entry)
    }
}

@Composable
private fun AuditLogCard(entry: AuditLogEntry) {
    val severityColor = when (entry.severity) {
        "CRITICAL" -> MaterialTheme.colorScheme.error
        "WARNING" -> MaterialTheme.colorScheme.tertiary
        else -> MaterialTheme.colorScheme.primary
    }
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(modifier = Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.Gavel, contentDescription = null, tint = severityColor, modifier = Modifier.size(28.dp))
            Spacer(modifier = Modifier.width(16.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    entry.eventTypeDisplay.ifBlank { entry.eventType },
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    buildString {
                        append(entry.userName ?: entry.userEmail ?: "نظام")
                        entry.ipAddress?.let { append(" • $it") }
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    entry.timestamp.take(19).replace('T', ' '),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.outline
                )
            }
            if (entry.riskScore > 0) {
                Surface(shape = RoundedCornerShape(6.dp), color = severityColor.copy(alpha = 0.15f)) {
                    Text(
                        "خطورة ${entry.riskScore}",
                        color = severityColor,
                        style = MaterialTheme.typography.labelSmall,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                    )
                }
            }
        }
    }
}
