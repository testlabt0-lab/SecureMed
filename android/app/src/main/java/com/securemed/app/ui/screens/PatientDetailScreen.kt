package com.securemed.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.PictureAsPdf
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.hilt.navigation.compose.hiltViewModel
import com.securemed.app.data.model.MedicalRecord
import com.securemed.app.data.model.Patient
import com.securemed.app.data.model.PatientFileInfo

/** Record types accepted by `MedicalRecord.RecordType` on the server. */
private val RECORD_TYPES = listOf(
    "DIAGNOSIS" to "تشخيص",
    "PRESCRIPTION" to "وصفة طبية",
    "LAB_ORDER" to "طلب تحاليل",
    "LAB_RESULT" to "نتيجة تحاليل",
    "IMAGING" to "تصوير طبي",
    "NOTES" to "ملاحظات",
    "VITALS" to "علامات حيوية",
    "PROCEDURE" to "إجراء طبي",
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PatientDetailScreen(
    patientId: String,
    onBack: () -> Unit,
    viewModel: PatientDetailViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    var showCreateDialog by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("تفاصيل المريض") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "رجوع")
                    }
                }
            )
        },
        floatingActionButton = {
            if (uiState is PatientDetailUiState.Success) {
                ExtendedFloatingActionButton(
                    onClick = {
                        viewModel.clearActionMessage()
                        showCreateDialog = true
                    },
                    icon = { Icon(Icons.Default.Add, contentDescription = null) },
                    text = { Text("سجل جديد") }
                )
            }
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

                        if (state.files.isNotEmpty()) {
                            item {
                                Text(
                                    text = "الملفات الطبية (${state.files.size})",
                                    style = MaterialTheme.typography.titleLarge,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(vertical = 8.dp)
                                )
                            }
                            items(state.files) { file ->
                                PatientFileCard(file = file)
                            }
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

                    state.actionMessage?.let { message ->
                        Snackbar(
                            modifier = Modifier.align(Alignment.BottomCenter).padding(16.dp),
                            action = {
                                TextButton(onClick = { viewModel.clearActionMessage() }) { Text("حسناً") }
                            }
                        ) { Text(message, color = MaterialTheme.colorScheme.error.takeIf { message.startsWith("تعذر") } ?: MaterialTheme.colorScheme.onSurface) }
                    }

                    if (showCreateDialog) {
                        CreateRecordDialog(
                            channels = state.channels,
                            inProgress = state.actionInProgress,
                            onDismiss = {
                                if (!state.actionInProgress) {
                                    showCreateDialog = false
                                    viewModel.clearActionMessage()
                                }
                            },
                            onSubmit = { channelId, title, type, content, critical ->
                                viewModel.createRecord(patientId, channelId, title, content, type, critical)
                                showCreateDialog = false
                            }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun CreateRecordDialog(
    channels: List<com.securemed.app.data.model.Channel>,
    inProgress: Boolean,
    onDismiss: () -> Unit,
    onSubmit: (channelId: String, title: String, recordType: String, content: String, isCritical: Boolean) -> Unit
) {
    var channelId by remember { mutableStateOf(channels.firstOrNull()?.id ?: "") }
    var channelExpanded by remember { mutableStateOf(false) }
    var title by remember { mutableStateOf("") }
    var content by remember { mutableStateOf("") }
    var recordType by remember { mutableStateOf(RECORD_TYPES.first().first) }
    var typeExpanded by remember { mutableStateOf(false) }
    var isCritical by remember { mutableStateOf(false) }
    var showEmptyChannelError by remember { mutableStateOf(false) }

    val valid = channelId.isNotBlank() && title.isNotBlank() && content.isNotBlank()

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            shape = RoundedCornerShape(16.dp),
            color = MaterialTheme.colorScheme.surface
        ) {
            Column(
                modifier = Modifier
                    .padding(20.dp)
                    .verticalScroll(rememberScrollState())
            ) {
                Text(
                    text = "سجل طبي جديد",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold
                )
                Spacer(modifier = Modifier.height(12.dp))

                if (channels.isEmpty()) {
                    Text(
                        text = "لا توجد قناة يمكنك الكتابة فيها لهذا المريض",
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodyMedium
                    )
                } else {
                    ExposedDropdownMenuBox(
                        expanded = channelExpanded,
                        onExpandedChange = { channelExpanded = it }
                    ) {
                        OutlinedTextField(
                            value = channels.firstOrNull { it.id == channelId }?.name ?: "",
                            onValueChange = {},
                            readOnly = true,
                            label = { Text("القناة") },
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(channelExpanded) },
                            modifier = Modifier.menuAnchor().fillMaxWidth()
                        )
                        ExposedDropdownMenu(
                            expanded = channelExpanded,
                            onDismissRequest = { channelExpanded = false }
                        ) {
                            channels.forEach { channel ->
                                DropdownMenuItem(
                                    text = { Text(channel.name) },
                                    onClick = {
                                        channelId = channel.id
                                        channelExpanded = false
                                    }
                                )
                            }
                        }
                    }
                    Spacer(modifier = Modifier.height(8.dp))

                    ExposedDropdownMenuBox(
                        expanded = typeExpanded,
                        onExpandedChange = { typeExpanded = it }
                    ) {
                        OutlinedTextField(
                            value = RECORD_TYPES.firstOrNull { it.first == recordType }?.second ?: recordType,
                            onValueChange = {},
                            readOnly = true,
                            label = { Text("نوع السجل") },
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(typeExpanded) },
                            modifier = Modifier.menuAnchor().fillMaxWidth()
                        )
                        ExposedDropdownMenu(
                            expanded = typeExpanded,
                            onDismissRequest = { typeExpanded = false }
                        ) {
                            RECORD_TYPES.forEach { (value, label) ->
                                DropdownMenuItem(
                                    text = { Text(label) },
                                    onClick = {
                                        recordType = value
                                        typeExpanded = false
                                    }
                                )
                            }
                        }
                    }
                    Spacer(modifier = Modifier.height(8.dp))

                    OutlinedTextField(
                        value = title,
                        onValueChange = { title = it },
                        label = { Text("العنوان") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(modifier = Modifier.height(8.dp))

                    OutlinedTextField(
                        value = content,
                        onValueChange = { content = it },
                        label = { Text("المحتوى السريري") },
                        minLines = 3,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(modifier = Modifier.height(8.dp))

                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = isCritical, onCheckedChange = { isCritical = it })
                        Text("حالة حرجة", style = MaterialTheme.typography.bodyMedium)
                    }

                    if (showEmptyChannelError) {
                        Text(
                            text = "أكمل العنوان والمحتوى أولاً",
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End
                ) {
                    TextButton(onClick = onDismiss, enabled = !inProgress) { Text("إلغاء") }
                    Spacer(modifier = Modifier.width(8.dp))
                    if (inProgress) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(24.dp),
                            strokeWidth = 2.dp
                        )
                    } else {
                        Button(
                            onClick = {
                                if (valid) onSubmit(channelId, title.trim(), recordType, content.trim(), isCritical)
                                else showEmptyChannelError = true
                            },
                            enabled = channels.isNotEmpty()
                        ) { Text("حفظ") }
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
fun PatientFileCard(file: PatientFileInfo) {
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
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .background(
                        MaterialTheme.colorScheme.secondaryContainer,
                        shape = RoundedCornerShape(8.dp)
                    ),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    Icons.Default.PictureAsPdf,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSecondaryContainer
                )
            }
            Spacer(modifier = Modifier.width(16.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = file.title.ifBlank { file.fileName },
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = "${file.fileTypeDisplay.ifBlank { file.fileType }} • ${formatFileSize(file.fileSize)}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            if (file.isCritical) {
                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = MaterialTheme.colorScheme.error.copy(alpha = 0.1f)
                ) {
                    Text(
                        "حرج",
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.labelSmall,
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                    )
                }
            }
        }
    }
}

private fun formatFileSize(bytes: Long): String = when {
    bytes >= 1_048_576 -> "%.1f م.ب".format(bytes / 1_048_576.0)
    bytes >= 1_024 -> "%.1f ك.ب".format(bytes / 1_024.0)
    else -> "$bytes بايت"
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
            verticalAlignment = Alignment.Top
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
                        text = "بواسطة: ${record.createdByName ?: "غير معروف"}",
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
