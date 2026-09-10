package com.securemed.app.ui.screens

import android.content.Intent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.PictureAsPdf
import androidx.compose.material.icons.filled.TableView
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import androidx.hilt.navigation.compose.hiltViewModel
import com.securemed.app.data.model.ReportCatalogItem
import java.io.File

/**
 * Report export screen (3-6's closing item): the role-filtered catalog from
 * `reports/list/`, each card offering PDF/Excel download. The downloaded file
 * opens through FileProvider — never a raw file:// URI.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportsScreen(onBack: () -> Unit, viewModel: ReportsViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    var selectedReport by remember { mutableStateOf<ReportCatalogItem?>(null) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("التقارير") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "رجوع")
                    }
                }
            )
        },
        snackbarHost = {
            Box {
                uiState.message?.let { message ->
                    Snackbar(
                        modifier = Modifier.padding(16.dp),
                        action = {
                            TextButton(onClick = { viewModel.clearMessage() }) { Text("حسناً") }
                        }
                    ) { Text(message) }
                }
            }
        }
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            when {
                uiState.isLoading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                uiState.errorMessage != null -> {
                    Column(
                        modifier = Modifier.align(Alignment.Center).padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(uiState.errorMessage ?: "", color = MaterialTheme.colorScheme.error)
                        Spacer(modifier = Modifier.height(12.dp))
                        Button(onClick = { viewModel.loadCatalog() }) { Text("إعادة المحاولة") }
                    }
                }
                uiState.reports.isEmpty() -> {
                    Text(
                        "لا توجد تقارير متاحة لدورك",
                        modifier = Modifier.align(Alignment.Center),
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                else -> {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize().padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        items(uiState.reports, key = { it.id }) { report ->
                            ReportCard(
                                report = report,
                                downloading = uiState.downloadingId == report.id,
                                onDownload = { format, start, end ->
                                    viewModel.download(report, format, start, end)
                                }
                            )
                        }
                    }
                }
            }

            // Open action after a successful download.
            uiState.downloadedFile?.let { file ->
                Snackbar(
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .padding(16.dp),
                    action = {
                        TextButton(
                            onClick = {
                                if (openReportFile(context, file)) {
                                    viewModel.clearMessage()
                                } else {
                                    android.widget.Toast.makeText(
                                        context,
                                        "لا يوجد تطبيق يفتح هذا النوع من الملفات",
                                        android.widget.Toast.LENGTH_LONG
                                    ).show()
                                }
                            }
                        ) { Text("فتح") }
                    },
                    dismissAction = {
                        TextButton(onClick = { viewModel.clearMessage() }) { Text("إغلاق") }
                    }
                ) { Text("تم تنزيل التقرير") }
            }
        }
    }

    selectedReport?.let { report ->
        DownloadOptionsDialog(
            report = report,
            onDismiss = { selectedReport = null },
            onDownload = { format, start, end ->
                selectedReport = null
                viewModel.download(report, format, start, end)
            }
        )
    }
}

@Composable
private fun ReportCard(
    report: ReportCatalogItem,
    downloading: Boolean,
    onDownload: (format: String, start: String?, end: String?) -> Unit
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
            Text(
                text = report.title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )
            if (report.description.isNotBlank()) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = report.description,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Spacer(modifier = Modifier.height(10.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
                verticalAlignment = Alignment.CenterVertically
            ) {
                if (downloading) {
                    CircularProgressIndicator(modifier = Modifier.size(22.dp), strokeWidth = 2.dp)
                } else {
                    report.formats.forEach { format ->
                        val isExcel = format == "excel"
                        OutlinedButton(
                            onClick = { onDownload(format, null, null) },
                            modifier = Modifier.padding(start = 8.dp)
                        ) {
                            Icon(
                                if (isExcel) Icons.Default.TableView else Icons.Default.PictureAsPdf,
                                contentDescription = null,
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(if (isExcel) "Excel" else "PDF")
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun DownloadOptionsDialog(
    report: ReportCatalogItem,
    onDismiss: () -> Unit,
    onDownload: (format: String, start: String?, end: String?) -> Unit
) {
    var format by remember { mutableStateOf("pdf") }
    var startDate by remember { mutableStateOf("") }
    var endDate by remember { mutableStateOf("") }
    var validationError by remember { mutableStateOf<String?>(null) }

    val datePattern = Regex("""\d{4}-\d{2}-\d{2}""")
    val datesValid = (startDate.isBlank() || datePattern.matches(startDate.trim())) &&
        (endDate.isBlank() || datePattern.matches(endDate.trim()))

    AlertDialog(
        onDismissRequest = onDismiss,
        icon = { Icon(Icons.Default.Download, contentDescription = null) },
        title = { Text("تنزيل: ${report.title}", fontWeight = FontWeight.Bold) },
        text = {
            Column {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    report.formats.forEach { option ->
                        FilterChip(
                            selected = format == option,
                            onClick = { format = option },
                            label = { Text(if (option == "excel") "Excel" else "PDF") }
                        )
                    }
                }
                Spacer(modifier = Modifier.height(10.dp))
                OutlinedTextField(
                    value = startDate,
                    onValueChange = { startDate = it },
                    label = { Text("من تاريخ (YYYY-MM-DD، اختياري)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(
                    value = endDate,
                    onValueChange = { endDate = it },
                    label = { Text("إلى تاريخ (YYYY-MM-DD، اختياري)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                validationError?.let {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (!datesValid) {
                        validationError = "صيغة التاريخ يجب أن تكون YYYY-MM-DD"
                    } else {
                        validationError = null
                        onDownload(format, startDate.trim(), endDate.trim())
                    }
                }
            ) { Text("تنزيل") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("إلغاء") }
        }
    )
}

/** Opens the downloaded export with whatever viewer the device has. */
internal fun openReportFile(context: android.content.Context, file: File): Boolean {
    val uri = FileProvider.getUriForFile(
        context, "${context.packageName}.fileprovider", file
    )
    val mime = if (file.extension == "xlsx") "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else "application/pdf"
    val intent = Intent(Intent.ACTION_VIEW).apply {
        setDataAndType(uri, mime)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
    }
    return runCatching { context.startActivity(intent) }.isSuccess
}
