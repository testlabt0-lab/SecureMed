package com.securemed.app.ui.screens

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Chat
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.UploadFile
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.hilt.navigation.compose.hiltViewModel

/** File types accepted by `MedicalFile.FileType` on the server. */
private val MEDICAL_FILE_TYPES = listOf(
    "XRAY" to "أشعة سينية",
    "MRI" to "رنين مغناطيسي",
    "CT_SCAN" to "تصوير مقطعي",
    "ULTRASOUND" to "موجات صوتية",
    "LAB_REPORT" to "تقرير مختبر",
    "DOCUMENT" to "مستند",
    "OTHER" to "أخرى",
)

/** Server cap (`validate_file_size`) — checked client-side too, with the message. */
private const val MAX_UPLOAD_BYTES = 20L * 1024 * 1024

private val ALLOWED_EXTENSIONS = setOf("jpg", "jpeg", "png", "gif", "pdf", "dicom", "dcm")

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChannelDetailScreen(
    channelId: String,
    onBack: () -> Unit,
    onOpenChat: () -> Unit = {}
) {
    val viewModel: ChannelDetailViewModel = hiltViewModel()
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current

    // Picked document, held until the metadata dialog is submitted.
    var pickedFile by remember { mutableStateOf<PickedDocument?>(null) }
    var showUploadDialog by remember { mutableStateOf(false) }

    val filePicker = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument()
    ) { uri: Uri? ->
        if (uri != null) {
            val doc = PickedDocument.read(context, uri)
            if (doc == null) {
                viewModel.clearUploadMessage()
                viewModel.reportLocalUploadProblem("تعذر قراءة الملف المحدد")
            } else {
                pickedFile = doc
                viewModel.clearUploadMessage()
                showUploadDialog = true
            }
        }
    }

    LaunchedEffect(channelId) {
        viewModel.loadChannel(channelId)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(state.channel?.name ?: "تفاصيل القناة") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "رجوع")
                    }
                },
                actions = {
                    IconButton(onClick = { viewModel.clearUploadMessage(); filePicker.launch(arrayOf("*/*")) }) {
                        Icon(Icons.Default.UploadFile, "رفع ملف طبي")
                    }
                    IconButton(onClick = onOpenChat) {
                        Icon(
                            Icons.AutoMirrored.Filled.Chat,
                            "محادثة القناة"
                        )
                    }
                }
            )
        }
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize()) {
            if (state.isLoading) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator()
                }
                return@Box
            }

            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
            // Channel info
            item {
                state.channel?.let { channel ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text(
                                text = channel.name,
                                style = MaterialTheme.typography.titleLarge,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = channel.description ?: "",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                AssistChip(
                                    onClick = {},
                                    label = { Text(channel.channelTypeDisplay) }
                                )
                                AssistChip(
                                    onClick = {},
                                    label = { Text(channel.statusDisplay) }
                                )
                                AssistChip(
                                    onClick = {},
                                    label = { Text("أولوية: ${channel.priority}") }
                                )
                            }
                            channel.currentUserRole?.let {
                                Spacer(modifier = Modifier.height(8.dp))
                                Surface(
                                    shape = RoundedCornerShape(8.dp),
                                    color = MaterialTheme.colorScheme.primaryContainer
                                ) {
                                    Text(
                                        text = "دورك: $it",
                                        style = MaterialTheme.typography.bodyMedium,
                                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)
                                    )
                                }
                            }
                        }
                    }
                }
            }

            // Members
            item {
                Text(
                    text = "الأعضاء (${state.members.size})",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(top = 8.dp)
                )
            }
            items(state.members) { member ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier
                                .size(36.dp)
                                .background(
                                    MaterialTheme.colorScheme.primaryContainer,
                                    RoundedCornerShape(50)
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = member.user.fullName.firstOrNull()?.toString() ?: "?",
                                color = MaterialTheme.colorScheme.onPrimaryContainer,
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = member.user.fullName,
                                style = MaterialTheme.typography.bodyLarge,
                                fontWeight = FontWeight.Medium
                            )
                            Text(
                                text = member.user.email,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = MaterialTheme.colorScheme.secondaryContainer
                        ) {
                            Text(
                                text = member.roleDisplay,
                                style = MaterialTheme.typography.labelSmall,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                            )
                        }
                    }
                }
            }

            // Medical records
            item {
                Text(
                    text = "السجلات الطبية (${state.records.size})",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(top = 8.dp)
                )
            }
            items(state.records) { record ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = record.title,
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.SemiBold
                            )
                            if (record.isCritical) {
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
                        Text(
                            text = record.content,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            maxLines = 2
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "بواسطة ${record.createdByName ?: "غير معروف"} • ${record.recordTypeDisplay}",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.outline
                        )
                    }
                }
            }

            // Security info
            item {
                Spacer(modifier = Modifier.height(8.dp))
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.3f)
                    )
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(
                            text = "🔒 معلومات الأمان",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "• DV (دور واحد لكل مستخدم): ✓",
                            style = MaterialTheme.typography.bodySmall
                        )
                        Text(
                            text = "• تشفير المحتوى: AES-256",
                            style = MaterialTheme.typography.bodySmall
                        )
                        Text(
                            text = "• WAF Protection: نشط",
                            style = MaterialTheme.typography.bodySmall
                        )
                        Text(
                            text = "• سجل التدقيق: نشط",
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
            }
        }

            state.uploadMessage?.let { message ->
                Snackbar(
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .padding(16.dp),
                    containerColor = if (state.uploadIsError) MaterialTheme.colorScheme.errorContainer
                    else MaterialTheme.colorScheme.primaryContainer,
                    action = {
                        TextButton(onClick = { viewModel.clearUploadMessage() }) { Text("حسناً") }
                    }
                ) {
                    Text(
                        message,
                        color = if (state.uploadIsError) MaterialTheme.colorScheme.onErrorContainer
                        else MaterialTheme.colorScheme.onPrimaryContainer
                    )
                }
            }
        }
    }

    if (showUploadDialog && pickedFile != null) {
        UploadFileDialog(
            picked = pickedFile!!,
            inProgress = state.uploadInProgress,
            onDismiss = {
                if (!state.uploadInProgress) {
                    showUploadDialog = false
                    viewModel.clearUploadMessage()
                }
            },
            onSubmit = { title, fileType, description ->
                showUploadDialog = false
                viewModel.uploadMedicalFile(
                    channelId = channelId,
                    patientId = null,
                    fileBytes = pickedFile!!.bytes,
                    fileName = pickedFile!!.displayName,
                    mimeType = pickedFile!!.mimeType,
                    title = title,
                    fileType = fileType,
                    description = description
                )
            }
        )
    }
}

/** A document picked from the device, already validated client-side. */
private data class PickedDocument(
    val bytes: ByteArray,
    val displayName: String,
    val mimeType: String
) {
    val extension: String get() = displayName.substringAfterLast('.', "").lowercase()

    companion object {
        /**
         * Reads and pre-validates a picked document: extension must be one the
         * server accepts, size under its 20MB cap. Null means "do not upload".
         */
        fun read(context: android.content.Context, uri: Uri): PickedDocument? = runCatching {
            val displayName = context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
                val idx = cursor.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                cursor.moveToFirst()
                if (idx >= 0) cursor.getString(idx) else null
            } ?: "ملف"
            val mimeType = context.contentResolver.getType(uri) ?: "application/octet-stream"
            val bytes = context.contentResolver.openInputStream(uri)?.use { it.readBytes() } ?: return null
            val ext = displayName.substringAfterLast('.', "").lowercase()
            if (ext !in ALLOWED_EXTENSIONS) return null
            if (bytes.size > MAX_UPLOAD_BYTES) return null
            PickedDocument(bytes, displayName, mimeType)
        }.getOrNull()
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun UploadFileDialog(
    picked: PickedDocument,
    inProgress: Boolean,
    onDismiss: () -> Unit,
    onSubmit: (title: String, fileType: String, description: String?) -> Unit
) {
    var title by remember { mutableStateOf(picked.displayName.substringBeforeLast('.')) }
    var fileType by remember {
        mutableStateOf(
            when (picked.extension) {
                "pdf" -> "DOCUMENT"
                "dicom", "dcm" -> "OTHER"
                else -> "DOCUMENT"
            }
        )
    }
    var typeExpanded by remember { mutableStateOf(false) }
    var description by remember { mutableStateOf("") }
    var validationError by remember { mutableStateOf<String?>(null) }

    Dialog(onDismissRequest = onDismiss) {
        Surface(shape = RoundedCornerShape(16.dp), color = MaterialTheme.colorScheme.surface) {
            Column(
                modifier = Modifier
                    .padding(20.dp)
                    .verticalScroll(rememberScrollState())
            ) {
                Text("رفع ملف طبي", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "${picked.displayName} • ${picked.bytes.size / 1024} ك.ب",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.height(12.dp))

                ExposedDropdownMenuBox(expanded = typeExpanded, onExpandedChange = { typeExpanded = it }) {
                    OutlinedTextField(
                        value = MEDICAL_FILE_TYPES.firstOrNull { it.first == fileType }?.second ?: fileType,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("نوع الملف") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(typeExpanded) },
                        modifier = Modifier.menuAnchor().fillMaxWidth()
                    )
                    ExposedDropdownMenu(expanded = typeExpanded, onDismissRequest = { typeExpanded = false }) {
                        MEDICAL_FILE_TYPES.forEach { (value, display) ->
                            DropdownMenuItem(
                                text = { Text(display) },
                                onClick = {
                                    fileType = value
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
                    value = description,
                    onValueChange = { description = it },
                    label = { Text("الوصف (اختياري)") },
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
                                if (title.isBlank()) validationError = "أدخل عنواناً للملف"
                                else onSubmit(title.trim(), fileType, description.trim().takeIf { it.isNotEmpty() })
                            }
                        ) { Text("رفع") }
                    }
                }
            }
        }
    }
}
