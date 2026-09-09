package com.securemed.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Close
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
import com.securemed.app.data.model.Appointment
import com.securemed.app.data.model.Patient
import com.securemed.app.data.model.User
import java.time.LocalDate
import java.time.LocalTime
import java.time.format.DateTimeFormatter

/** Appointment types and priorities (`Appointment.AppointmentType`/`Priority`). */
private val APPOINTMENT_TYPES = listOf(
    "INITIAL" to "كشف أول",
    "FOLLOW_UP" to "متابعة",
    "CONSULTATION" to "استشارة",
    "LAB" to "تحاليل مختبر",
    "IMAGING" to "أشعة / تصوير",
    "PROCEDURE" to "إجراء طبي",
    "EMERGENCY" to "طارئة",
    "TELEMEDICINE" to "طب عن بُعد",
)

private val APPOINTMENT_PRIORITIES = listOf(
    "LOW" to "منخفضة",
    "MEDIUM" to "متوسطة",
    "HIGH" to "عالية",
    "URGENT" to "عاجلة",
)

/** Statuses the server still allows cancelling. */
private val CANCELLABLE_STATUSES = setOf("SCHEDULED", "CONFIRMED", "RESCHEDULED")

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppointmentsScreen(
    onBack: () -> Unit,
    viewModel: AppointmentsViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    val appointments = viewModel.appointmentsPagingFlow.collectAsLazyPagingItems()
    var showBookingDialog by remember { mutableStateOf(false) }
    var cancellingAppointment by remember { mutableStateOf<Appointment?>(null) }

    // A booking/cancel that succeeded must be visible in the list; the Pager
    // caches its flow, so an explicit refresh invalidates the source.
    LaunchedEffect(Unit) {
        viewModel.refreshRequests.collect { appointments.refresh() }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("المواعيد") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "رجوع")
                    }
                }
            )
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = { viewModel.clearMessage(); showBookingDialog = true },
                icon = { Icon(Icons.Default.CalendarMonth, contentDescription = null) },
                text = { Text("موعد جديد") }
            )
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            val refreshError = appointments.loadState.refresh as? LoadState.Error
            when {
                appointments.loadState.refresh is LoadState.Loading && appointments.itemCount == 0 -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                refreshError != null && appointments.itemCount == 0 -> {
                    Column(
                        modifier = Modifier.align(Alignment.Center),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            ApiErrors.messageFor(refreshError.error, "حدث خطأ أثناء جلب المواعيد"),
                            color = MaterialTheme.colorScheme.error
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        Button(onClick = { appointments.retry() }) { Text("إعادة المحاولة") }
                    }
                }
                else -> {
                    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
                        if (appointments.itemCount == 0) {
                            Text(
                                "لا توجد مواعيد حالياً.",
                                modifier = Modifier.padding(16.dp),
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        } else {
                            LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                                items(appointments.itemCount) { index ->
                                    appointments[index]?.let { appointment ->
                                        AppointmentCard(
                                            appointment = appointment,
                                            onCancel = {
                                                if (appointment.status in CANCELLABLE_STATUSES) {
                                                    viewModel.clearMessage()
                                                    cancellingAppointment = appointment
                                                }
                                            }
                                        )
                                    }
                                }
                                if (appointments.loadState.append is LoadState.Loading) {
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

            if (showBookingDialog) {
                BookingDialog(
                    inProgress = uiState.actionInProgress,
                    onDismiss = {
                        if (!uiState.actionInProgress) {
                            showBookingDialog = false
                            viewModel.clearMessage()
                        }
                    },
                    onLoadOptions = viewModel::prepareBookingData,
                    onSubmit = { patientId, doctorId, type, priority, scheduledAt, duration, title, notes ->
                        viewModel.createAppointment(patientId, doctorId, type, priority, scheduledAt, duration, title, notes)
                        showBookingDialog = false
                    }
                )
            }

            cancellingAppointment?.let { appointment ->
                CancelAppointmentDialog(
                    appointment = appointment,
                    inProgress = uiState.actionInProgress,
                    onDismiss = {
                        if (!uiState.actionInProgress) {
                            cancellingAppointment = null
                            viewModel.clearMessage()
                        }
                    },
                    onConfirm = { reason ->
                        viewModel.cancelAppointment(appointment.id, reason)
                        cancellingAppointment = null
                    }
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AppointmentOptionDropdown(
    label: String,
    selectedLabel: String,
    options: List<Pair<String, String>>,
    expanded: Boolean,
    onExpandedChange: (Boolean) -> Unit,
    onSelect: (String) -> Unit
) {
    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = onExpandedChange) {
        OutlinedTextField(
            value = selectedLabel,
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
            modifier = Modifier.menuAnchor().fillMaxWidth()
        )
        ExposedDropdownMenu(expanded = expanded, onDismissRequest = { onExpandedChange(false) }) {
            options.forEach { (value, display) ->
                DropdownMenuItem(
                    text = { Text(display) },
                    onClick = {
                        onSelect(value)
                        onExpandedChange(false)
                    }
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun BookingDialog(
    inProgress: Boolean,
    onDismiss: () -> Unit,
    onLoadOptions: ((List<Patient>, List<User>) -> Unit) -> Unit,
    onSubmit: (patientId: String, doctorId: String, type: String, priority: String, scheduledAt: String, durationMinutes: Int, title: String, notes: String?) -> Unit,
    /**
     * When booking *from a patient page* the patient is fixed — their name
     * renders read-only and the patient dropdown disappears, so the only
     * choices left are clinical ones.
     */
    lockedPatient: Patient? = null
) {
    var patients by remember { mutableStateOf<List<Patient>>(emptyList()) }
    var doctors by remember { mutableStateOf<List<User>>(emptyList()) }
    var loaded by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        onLoadOptions { p, d ->
            patients = p
            doctors = d
            loaded = true
        }
    }

    var patientId by remember { mutableStateOf(lockedPatient?.id) }
    var doctorId by remember { mutableStateOf<String?>(null) }
    var patientExpanded by remember { mutableStateOf(false) }
    var doctorExpanded by remember { mutableStateOf(false) }
    var typeExpanded by remember { mutableStateOf(false) }
    var priorityExpanded by remember { mutableStateOf(false) }
    var appointmentType by remember { mutableStateOf("INITIAL") }
    var priority by remember { mutableStateOf("MEDIUM") }

    var dateText by remember { mutableStateOf(LocalDate.now().plusDays(1).toString()) }
    var timeText by remember { mutableStateOf("09:00") }
    var durationText by remember { mutableStateOf("30") }
    var title by remember { mutableStateOf("") }
    var notes by remember { mutableStateOf("") }
    var validationError by remember { mutableStateOf<String?>(null) }

    val scheduledAt: String? = run {
        val date = runCatching { LocalDate.parse(dateText.trim()) }.getOrNull()
        val time = runCatching {
            LocalTime.parse(timeText.trim(), DateTimeFormatter.ofPattern("HH:mm"))
        }.getOrNull()
        if (date != null && time != null) "$date${time.format(DateTimeFormatter.ofPattern("HH:mm:ss"))}" else null
    }
    val duration = durationText.trim().toIntOrNull()

    Dialog(onDismissRequest = onDismiss) {
        Surface(shape = RoundedCornerShape(16.dp), color = MaterialTheme.colorScheme.surface) {
            Column(
                modifier = Modifier
                    .padding(20.dp)
                    .verticalScroll(rememberScrollState())
            ) {
                Text("حجز موعد جديد", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(12.dp))

                if (!loaded) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 16.dp),
                        horizontalArrangement = Arrangement.Center
                    ) { CircularProgressIndicator() }
                } else {
                    if (lockedPatient != null) {
                        OutlinedTextField(
                            value = lockedPatient.fullName,
                            onValueChange = {},
                            readOnly = true,
                            label = { Text("المريض") },
                            modifier = Modifier.fillMaxWidth()
                        )
                    } else {
                        AppointmentOptionDropdown(
                            label = "المريض",
                            selectedLabel = patients.firstOrNull { it.id == patientId }?.fullName ?: "",
                            options = patients.map { it.id to it.fullName },
                            expanded = patientExpanded,
                            onExpandedChange = { patientExpanded = it },
                            onSelect = { patientId = it }
                        )
                    }
                    Spacer(modifier = Modifier.height(8.dp))

                    AppointmentOptionDropdown(
                        label = "الطبيب",
                        selectedLabel = doctors.firstOrNull { it.id == doctorId }?.fullName ?: "",
                        options = doctors.map { it.id to (it.fullName.ifBlank { it.email }) },
                        expanded = doctorExpanded,
                        onExpandedChange = { doctorExpanded = it },
                        onSelect = { doctorId = it }
                    )
                    Spacer(modifier = Modifier.height(8.dp))

                    AppointmentOptionDropdown(
                        label = "نوع الموعد",
                        selectedLabel = APPOINTMENT_TYPES.firstOrNull { it.first == appointmentType }?.second ?: appointmentType,
                        options = APPOINTMENT_TYPES,
                        expanded = typeExpanded,
                        onExpandedChange = { typeExpanded = it },
                        onSelect = { appointmentType = it }
                    )
                    Spacer(modifier = Modifier.height(8.dp))

                    AppointmentOptionDropdown(
                        label = "الأولوية",
                        selectedLabel = APPOINTMENT_PRIORITIES.firstOrNull { it.first == priority }?.second ?: priority,
                        options = APPOINTMENT_PRIORITIES,
                        expanded = priorityExpanded,
                        onExpandedChange = { priorityExpanded = it },
                        onSelect = { priority = it }
                    )
                    Spacer(modifier = Modifier.height(8.dp))

                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(
                            value = dateText,
                            onValueChange = { dateText = it },
                            label = { Text("التاريخ (YYYY-MM-DD)") },
                            singleLine = true,
                            modifier = Modifier.weight(1f)
                        )
                        OutlinedTextField(
                            value = timeText,
                            onValueChange = { timeText = it },
                            label = { Text("الوقت (HH:mm)") },
                            singleLine = true,
                            modifier = Modifier.weight(1f)
                        )
                    }
                    Spacer(modifier = Modifier.height(8.dp))

                    OutlinedTextField(
                        value = durationText,
                        onValueChange = { durationText = it.filter { c -> c.isDigit() }.take(3) },
                        label = { Text("المدة (دقيقة)") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(modifier = Modifier.height(8.dp))

                    OutlinedTextField(
                        value = title,
                        onValueChange = { title = it },
                        label = { Text("العنوان (اختياري)") },
                        singleLine = true,
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

                    if (patients.isEmpty() && lockedPatient == null) {
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
                                val error = when {
                                    patientId == null -> "اختر المريض"
                                    doctorId == null -> "اختر الطبيب"
                                    scheduledAt == null -> "صيغة التاريخ/الوقت غير صحيحة"
                                    duration == null || duration <= 0 -> "المدة غير صحيحة"
                                    else -> null
                                }
                                if (error != null) {
                                    validationError = error
                                } else {
                                    validationError = null
                                    onSubmit(
                                        patientId!!, doctorId!!, appointmentType, priority,
                                        scheduledAt!!, duration!!, title.trim(), notes.trim().takeIf { it.isNotEmpty() }
                                    )
                                }
                            },
                            enabled = loaded && (patients.isNotEmpty() || lockedPatient != null)
                        ) { Text("حجز") }
                    }
                }
            }
        }
    }
}

@Composable
private fun CancelAppointmentDialog(
    appointment: Appointment,
    inProgress: Boolean,
    onDismiss: () -> Unit,
    onConfirm: (reason: String?) -> Unit
) {
    var reason by remember { mutableStateOf("") }

    Dialog(onDismissRequest = onDismiss) {
        Surface(shape = RoundedCornerShape(16.dp), color = MaterialTheme.colorScheme.surface) {
            Column(modifier = Modifier.padding(20.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Close, contentDescription = null, tint = MaterialTheme.colorScheme.error)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("إلغاء الموعد", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                }
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    "الموعد: ${appointment.patientName ?: ""} — ${appointment.scheduledAt.take(16).replace('T', ' ')}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.height(12.dp))
                OutlinedTextField(
                    value = reason,
                    onValueChange = { reason = it },
                    label = { Text("سبب الإلغاء (اختياري)") },
                    minLines = 2,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(16.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End, verticalAlignment = Alignment.CenterVertically) {
                    TextButton(onClick = onDismiss, enabled = !inProgress) { Text("رجوع") }
                    Spacer(modifier = Modifier.width(8.dp))
                    if (inProgress) {
                        CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
                    } else {
                        Button(
                            onClick = { onConfirm(reason.trim().takeIf { it.isNotEmpty() }) },
                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                        ) { Text("إلغاء الموعد") }
                    }
                }
            }
        }
    }
}

@Composable
fun AppointmentCard(
    appointment: Appointment,
    onCancel: () -> Unit = {}
) {
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
                imageVector = Icons.Default.CalendarMonth,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.secondary,
                modifier = Modifier.size(32.dp)
            )
            Spacer(modifier = Modifier.width(16.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = appointment.patientName ?: "مريض غير معروف",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    // The server already localises the type; fall back to the
                    // raw enum only if an older build omits the display field.
                    text = "${appointment.scheduledAt.take(16).replace('T', ' ')} — " +
                        (appointment.typeDisplay ?: appointment.appointmentType),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = "الطبيب: ${appointment.doctorName ?: "طبيب غير معروف"} | " +
                        "الحالة: ${appointment.statusDisplay ?: appointment.status}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            if (appointment.status in CANCELLABLE_STATUSES) {
                TextButton(onClick = onCancel, enabled = true) {
                    Text("إلغاء", color = MaterialTheme.colorScheme.error)
                }
            }
        }
    }
}
