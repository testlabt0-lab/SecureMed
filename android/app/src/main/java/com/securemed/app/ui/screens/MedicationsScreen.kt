package com.securemed.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Medication
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.model.*
import com.securemed.app.reminders.ReminderScheduler
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.time.LocalDate

// ============================================================
// ViewModel
// ============================================================

class MedicationsViewModel : ViewModel() {
    private val repository = SecureMedRepository()

    data class MedicationsState(
        val isLoading: Boolean = true,
        val todayDoses: List<TodayDose> = emptyList(),
        val medications: List<Medication> = emptyList(),
        val patients: List<Patient> = emptyList(),
        val adherence: AdherenceStats? = null,
        val message: String? = null,
        val error: String? = null,
        val canPrescribe: Boolean = false
    )

    private val _state = MutableStateFlow(MedicationsState())
    val state: StateFlow<MedicationsState> = _state

    init {
        loadAll()
    }

    fun loadAll() {
        _state.value = _state.value.copy(isLoading = true, error = null)
        viewModelScope.launch {
            val doses = repository.getTodayDoses()
            val meds = repository.getMedications()
            val patients = repository.getPatients()
            val adherence = repository.getAdherence()

            val role = com.securemed.app.data.local.SecurePreferences.userRole ?: ""
            _state.value = MedicationsState(
                isLoading = false,
                todayDoses = doses.getOrDefault(TodayDosesResponse()).doses,
                medications = meds.getOrDefault(emptyList()),
                patients = patients.getOrDefault(emptyList()),
                adherence = adherence.getOrNull(),
                canPrescribe = role in listOf(
                    "SUPER_ADMIN", "HOSPITAL_ADMIN", "DOCTOR"
                ),
                error = if (doses.isFailure && meds.isFailure) "فشل تحميل الأدوية" else null
            )

            // Mirror the plan into the reminder scheduler (alarms even when
            // the app is closed, and after reboot via BootReceiver).
            meds.getOrDefault(emptyList())
                .filter { it.isActive }
                .forEach { ReminderScheduler(nullAnyContext()).scheduleNext(it) }
        }
    }

    /** The scheduler needs a Context — resolve it lazily via the app. */
    private fun nullAnyContext(): android.content.Context =
        com.securemed.app.SecureMedApp.instance!!

    fun logDose(dose: TodayDose, status: String) {
        viewModelScope.launch {
            repository.logDose(dose.medicationId, dose.scheduledFor, status)
                .onSuccess {
                    _state.value = _state.value.copy(
                        message = if (status == "TAKEN") "✓ تم تسجيل تناول ${dose.medicationName}"
                        else "تم تسجيل تخطي ${dose.medicationName}"
                    )
                    loadAll()
                }
                .onFailure { error ->
                    _state.value = _state.value.copy(
                        error = error.message ?: "فشل تسجيل الجرعة"
                    )
                }
        }
    }

    fun createMedication(
        patient: Patient,
        name: String,
        dosage: String,
        doseTimes: String,
        instructions: String,
        onDone: (Boolean) -> Unit
    ) {
        viewModelScope.launch {
            repository.createMedication(
                MedicationCreateRequest(
                    patient = patient.id,
                    name = name,
                    dosage = dosage,
                    doseTimes = doseTimes,
                    startDate = LocalDate.now().toString(),
                    instructions = instructions
                )
            )
                .onSuccess {
                    _state.value = _state.value.copy(
                        message = "✓ أُضيف الدواء $name — ستصل تذكيرات في مواعيدها"
                    )
                    loadAll()
                    onDone(true)
                }
                .onFailure { error ->
                    _state.value = _state.value.copy(
                        error = error.message ?: "فشل إضافة الدواء"
                    )
                    onDone(false)
                }
        }
    }

    fun clearMessage() {
        _state.value = _state.value.copy(message = null, error = null)
    }
}

// ============================================================
// Screen
// ============================================================

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MedicationsScreen(
    onBack: () -> Unit
) {
    val viewModel: MedicationsViewModel = viewModel()
    val state by viewModel.state.collectAsState()
    var showAddDialog by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("الأدوية والتذكيرات") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, "رجوع")
                    }
                },
                actions = {
                    IconButton(onClick = { viewModel.loadAll() }) {
                        Icon(Icons.Default.Refresh, "تحديث")
                    }
                    if (state.canPrescribe) {
                        IconButton(onClick = { showAddDialog = true }) {
                            Icon(Icons.Default.Add, "إضافة دواء")
                        }
                    }
                }
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Status messages
            state.message?.let { message ->
                item {
                    MessageCard(
                        text = message,
                        container = MaterialTheme.colorScheme.primaryContainer,
                        content = MaterialTheme.colorScheme.onPrimaryContainer,
                        onDismiss = { viewModel.clearMessage() }
                    )
                }
            }
            state.error?.let { error ->
                item {
                    MessageCard(
                        text = "⚠️ $error",
                        container = MaterialTheme.colorScheme.errorContainer,
                        content = MaterialTheme.colorScheme.onErrorContainer,
                        onDismiss = { viewModel.clearMessage() }
                    )
                }
            }

            if (state.isLoading) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 40.dp),
                        contentAlignment = Alignment.Center
                    ) { CircularProgressIndicator() }
                }
                return@LazyColumn
            }

            // Adherence summary
            state.adherence?.let { adherence ->
                item { AdherenceCard(adherence) }
            }

            // Today's doses
            item {
                Text(
                    "جرعات اليوم (${state.todayDoses.size})",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
            }
            if (state.todayDoses.isEmpty()) {
                item {
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Text(
                            "لا توجد جرعات مجدولة اليوم — أضف خطة دواء أو استمتع بيوم بلا أدوية",
                            modifier = Modifier.padding(16.dp),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
            items(state.todayDoses, key = { it.medicationId + it.scheduledFor }) { dose ->
                DoseCard(
                    dose = dose,
                    onTaken = { viewModel.logDose(dose, "TAKEN") },
                    onSkip = { viewModel.logDose(dose, "SKIPPED") }
                )
            }

            // Active medications
            item {
                Text(
                    "خطط الأدوية النشطة (${state.medications.size})",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(top = 8.dp)
                )
            }
            if (state.medications.isEmpty()) {
                item {
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Text(
                            "لا توجد أدوية مسجلة بعد",
                            modifier = Modifier.padding(16.dp),
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
            items(state.medications, key = { it.id }) { medication ->
                MedicationCard(medication)
            }
        }
    }

    if (showAddDialog) {
        AddMedicationDialog(
            patients = state.patients,
            onDismiss = { showAddDialog = false },
            onCreate = { patient, name, dosage, times, instructions ->
                viewModel.createMedication(patient, name, dosage, times, instructions) {
                    showAddDialog = false
                }
            }
        )
    }
}

// ============================================================
// Components
// ============================================================

@Composable
private fun MessageCard(
    text: String,
    container: androidx.compose.ui.graphics.Color,
    content: androidx.compose.ui.graphics.Color,
    onDismiss: () -> Unit
) {
    Card(modifier = Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = container)) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(text, color = content, modifier = Modifier.weight(1f))
            IconButton(onClick = onDismiss) {
                Icon(Icons.Default.Close, "إغلاق", tint = content)
            }
        }
    }
}

@Composable
private fun AdherenceCard(adherence: AdherenceStats) {
    val percent = adherence.adherencePercent
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (percent >= 80) MaterialTheme.colorScheme.secondaryContainer
            else MaterialTheme.colorScheme.tertiaryContainer
        )
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                "الالتزام خلال 7 أيام",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold
            )
            Spacer(Modifier.height(6.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    "$percent%",
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold
                )
                Spacer(Modifier.width(12.dp))
                Text(
                    "${adherence.takenDoses} من ${adherence.totalDoses} جرعة تم تناولها",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Spacer(Modifier.height(8.dp))
            LinearProgressIndicator(
                progress = { (percent / 100.0).toFloat() },
                modifier = Modifier.fillMaxWidth()
            )
        }
    }
}

@Composable
private fun DoseCard(dose: TodayDose, onTaken: () -> Unit, onSkip: () -> Unit) {
    val statusColor = when (dose.status) {
        "TAKEN" -> MaterialTheme.colorScheme.secondary
        "SKIPPED" -> MaterialTheme.colorScheme.tertiary
        "MISSED" -> MaterialTheme.colorScheme.error
        else -> MaterialTheme.colorScheme.outline
    }
    val statusText = when (dose.status) {
        "TAKEN" -> "✓ تم تناوله"
        "SKIPPED" -> "تم تخطيه"
        "MISSED" -> "فائت"
        else -> "قادم"
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Time bubble
            Box(
                modifier = Modifier
                    .size(52.dp)
                    .background(statusColor.copy(alpha = 0.12f), RoundedCornerShape(12.dp)),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    dose.time,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    color = statusColor
                )
            }
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    dose.medicationName,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    "${dose.dosage} • ${dose.patientName}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    statusText,
                    style = MaterialTheme.typography.labelSmall,
                    color = statusColor
                )
            }
            if (dose.status == "PENDING") {
                FilledTonalIconButton(onClick = onTaken) {
                    Icon(Icons.Default.CheckCircle, "تم التناول", tint = MaterialTheme.colorScheme.secondary)
                }
                Spacer(Modifier.width(6.dp))
                FilledTonalIconButton(onClick = onSkip) {
                    Icon(Icons.Default.Cancel, "تخطي", tint = MaterialTheme.colorScheme.tertiary)
                }
            }
        }
    }
}

@Composable
private fun MedicationCard(medication: Medication) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .background(
                        MaterialTheme.colorScheme.primaryContainer,
                        RoundedCornerShape(12.dp)
                    ),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    Icons.Default.Medication, null,
                    tint = MaterialTheme.colorScheme.onPrimaryContainer
                )
            }
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    medication.name,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    "${medication.dosage} • ${medication.patientName}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    "المواعيد: ${medication.times.joinToString("، ")} • بواسطة ${medication.prescribedByName}",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.outline
                )
                medication.instructions.takeIf { it.isNotBlank() }?.let {
                    Text(
                        it,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 2
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AddMedicationDialog(
    patients: List<Patient>,
    onDismiss: () -> Unit,
    onCreate: (Patient, String, String, String, String) -> Unit
) {
    var selectedPatient by remember { mutableStateOf<Patient?>(null) }
    var patientExpanded by remember { mutableStateOf(false) }
    var name by remember { mutableStateOf("") }
    var dosage by remember { mutableStateOf("") }
    var times by remember { mutableStateOf("08:00,20:00") }
    var instructions by remember { mutableStateOf("") }
    val validTimes = remember(times) { validateTimes(times) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("إضافة دواء") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                ExposedDropdownMenuBox(
                    expanded = patientExpanded,
                    onExpandedChange = { patientExpanded = it }
                ) {
                    OutlinedTextField(
                        value = selectedPatient?.fullName ?: "",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("المريض") },
                        trailingIcon = {
                            ExposedDropdownMenuDefaults.TrailingIcon(patientExpanded)
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .menuAnchor()
                    )
                    ExposedDropdownMenu(
                        expanded = patientExpanded,
                        onDismissRequest = { patientExpanded = false }
                    ) {
                        patients.forEach { patient ->
                            DropdownMenuItem(
                                text = { Text(patient.fullName) },
                                onClick = {
                                    selectedPatient = patient
                                    patientExpanded = false
                                }
                            )
                        }
                    }
                }

                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("اسم الدواء") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = dosage,
                    onValueChange = { dosage = it },
                    label = { Text("الجرعة (مثال: 500 ملغ)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = times,
                    onValueChange = { times = it },
                    label = { Text("أوقات الجرعات (24 ساعة)") },
                    supportingText = {
                        Text(
                            if (validTimes) "مثال: 08:00,14:00,20:00"
                            else "⚠️ صيغة غير صالحة — استخدم HH:MM مفصولة بفواصل",
                            color = if (validTimes) MaterialTheme.colorScheme.onSurfaceVariant
                            else MaterialTheme.colorScheme.error
                        )
                    },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = instructions,
                    onValueChange = { instructions = it },
                    label = { Text("تعليمات (اختياري)") },
                    minLines = 2,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    selectedPatient?.let { patient ->
                        onCreate(patient, name.trim(), dosage.trim(), times.trim(), instructions.trim())
                    }
                },
                enabled = selectedPatient != null && name.isNotBlank() &&
                    dosage.isNotBlank() && validTimes
            ) { Text("إضافة") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("إلغاء") }
        }
    )
}

/** True when every comma-separated token is a valid HH:MM 24h time. */
private fun validateTimes(raw: String): Boolean {
    val parts = raw.split(',').map { it.trim() }.filter { it.isNotEmpty() }
    if (parts.isEmpty()) return false
    return parts.all { part ->
        val regex = Regex("""^([01]\d|2[0-3]):([0-5]\d)$""")
        regex.matches(part)
    }
}
