package com.securemed.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.securemed.app.data.model.DrugInteractionResponse
import com.securemed.app.data.model.RuleHit
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DrugInteractionBottomSheet(
    patientName: String? = null,
    patientId: String? = null,
    initialMedications: List<String> = emptyList(),
    patientAllergies: String? = null,
    onDismiss: () -> Unit,
    onCheckInteractions: suspend (List<String>, String?) -> DrugInteractionResponse
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var medicationList by remember { mutableStateOf(initialMedications.toMutableList()) }
    var newMedName by remember { mutableStateOf("") }
    var isChecking by remember { mutableStateOf(false) }
    var checkResult by remember { mutableStateOf<DrugInteractionResponse?>(null) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    val coroutineScope = rememberCoroutineScope()

    // Trigger check on launch if initial meds provided
    LaunchedEffect(Unit) {
        if (medicationList.size >= 2) {
            isChecking = true
            try {
                checkResult = onCheckInteractions(medicationList, patientId)
            } catch (e: Exception) {
                errorMessage = e.localizedMessage
            } finally {
                isChecking = false
            }
        }
    }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        dragHandle = { BottomSheetDefaults.DragHandle() },
        containerColor = MaterialTheme.colorScheme.surface
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp, vertical = 12.dp)
                .fillMaxHeight(0.88f)
        ) {
            InteractionSheetHeader(patientName = patientName, onDismiss = onDismiss)

            // Patient Allergies Alert if present
            if (!patientAllergies.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(10.dp))
                AllergyAlert(patientAllergies = patientAllergies)
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Add Drug Input
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                OutlinedTextField(
                    value = newMedName,
                    onValueChange = { newMedName = it },
                    label = { Text("اسم الدواء (علمي أو تجاري)") },
                    placeholder = { Text("مثال: وارفارين، أسبرين، كيتوفان...") },
                    singleLine = true,
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(12.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Button(
                    onClick = {
                        val trimmed = newMedName.trim()
                        if (trimmed.isNotBlank() && !medicationList.contains(trimmed)) {
                            medicationList.add(trimmed)
                            newMedName = ""
                        }
                    },
                    enabled = newMedName.isNotBlank(),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.height(54.dp)
                ) {
                    Icon(Icons.Default.Add, contentDescription = "إضافة")
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Current Chips
            if (medicationList.isNotEmpty()) {
                Text(
                    text = "الأدوية المحددة للفحص (${medicationList.size}):",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold
                )
                Spacer(modifier = Modifier.height(6.dp))
                MedicationChips(
                    medicationList = medicationList,
                    onRemove = { med ->
                        medicationList = medicationList.toMutableList().apply { remove(med) }
                    }
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Run Check Button
            Button(
                onClick = {
                    isChecking = true
                    errorMessage = null
                    coroutineScope.launch {
                        try {
                            checkResult = onCheckInteractions(medicationList, patientId)
                        } catch (e: Exception) {
                            errorMessage = e.localizedMessage ?: "فشل الفحص الدوائي"
                        } finally {
                            isChecking = false
                        }
                    }
                },
                enabled = medicationList.size >= 2 && !isChecking,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            ) {
                if (isChecking) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        strokeWidth = 2.dp,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("جاري الفحص السريري بالذكاء الاصطناعي...")
                } else {
                    Icon(Icons.Default.CheckCircle, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("فحص التعارضات الآن")
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            InteractionResults(
                modifier = Modifier.weight(1f),
                result = checkResult,
                errorMessage = errorMessage
            )
        }
    }
}

@Composable
private fun InteractionSheetHeader(patientName: String?, onDismiss: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(MaterialTheme.colorScheme.primaryContainer),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    Icons.Default.Medication,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onPrimaryContainer
                )
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column {
                Text(
                    text = "فاحص التعارضات الدوائية الذكي",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                if (!patientName.isNullOrBlank()) {
                    Text(
                        text = "المريض: $patientName",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
        IconButton(onClick = onDismiss) {
            Icon(Icons.Default.Close, contentDescription = "إغلاق")
        }
    }
}

@Composable
private fun AllergyAlert(patientAllergies: String) {
    Surface(
        shape = RoundedCornerShape(8.dp),
        color = MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.6f)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                Icons.Default.Warning,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.error,
                modifier = Modifier.size(18.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "حساسيات المريض المسجلة: $patientAllergies",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onErrorContainer,
                fontWeight = FontWeight.SemiBold
            )
        }
    }
}

@Composable
private fun MedicationChips(medicationList: List<String>, onRemove: (String) -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        medicationList.forEach { med ->
            InputChip(
                selected = false,
                onClick = { },
                label = { Text(med) },
                trailingIcon = {
                    Icon(
                        Icons.Default.Close,
                        contentDescription = "حذف",
                        modifier = Modifier
                            .size(16.dp)
                            .clickable { onRemove(med) }
                    )
                },
                shape = RoundedCornerShape(8.dp)
            )
        }
    }
}

@Composable
private fun InteractionResults(
    modifier: Modifier = Modifier,
    result: DrugInteractionResponse?,
    errorMessage: String?
) {
    Column(modifier = modifier.fillMaxWidth()) {
        // Results View
        if (errorMessage != null) {
            Text(
                text = errorMessage,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodySmall
            )
        }

        if (result != null) {
            LazyColumn(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
            // Overall banner
            item {
                if (result.hasSevere) {
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = MaterialTheme.colorScheme.errorContainer,
                        border = androidx.compose.foundation.BorderStroke(
                            1.dp,
                            MaterialTheme.colorScheme.error
                        )
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(14.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                Icons.Default.Dangerous,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.error,
                                modifier = Modifier.size(28.dp)
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text(
                                    text = "تفاعل حرج وخطير مرصود!",
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.error
                                )
                                Text(
                                    text = "تم رصد تعارض دوائي قد يهدد سلامة المريض. يرجى تعديل الجرعات أو اختيار بدائل.",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onErrorContainer
                                )
                            }
                        }
                    }
                } else if (result.ruleBased.isEmpty() && (result.aiReview?.findings.isNullOrEmpty())) {
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = Color(0xFFE8F5E9),
                        border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFF81C784))
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(14.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                Icons.Default.CheckCircle,
                                contentDescription = null,
                                tint = Color(0xFF2E7D32),
                                modifier = Modifier.size(26.dp)
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text(
                                    text = "مجموعة الأدوية آمنة",
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF1B5E20)
                                )
                                Text(
                                    text = "لم يتم العثور على أي تعارضات خطيرة معروفة بين هذه الأدوية.",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = Color(0xFF2E7D32)
                                )
                            }
                        }
                    }
                }
            }

            // Rule hits
            if (result.ruleBased.isNotEmpty()) {
                item {
                    Text(
                        text = "التفاعلات المؤكدة بقواعد الصيدلة السريرية:",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold
                    )
                }
                items(result.ruleBased) { hit ->
                    RuleHitCard(hit)
                }
            }

            // AI Review findings
            val aiReview = result.aiReview
            if (aiReview != null && aiReview.findings.isNotEmpty()) {
                item {
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "ملاحظات الذكاء الاصطناعي السريرية:",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold
                    )
                    if (aiReview.summary.isNotBlank()) {
                        Text(
                            text = aiReview.summary,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(top = 2.dp, bottom = 6.dp)
                        )
                    }
                }
                items(aiReview.findings) { finding ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                        )
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = finding.medications.joinToString(" + "),
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.Bold
                                )
                                SeverityBadge(finding.severity)
                            }
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = finding.note,
                                style = MaterialTheme.typography.bodySmall
                            )
                        }
                    }
                }
            }

            // Disclaimer
            item {
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = result.disclaimer,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.outline,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }
        }
    }
}

@Composable
private fun RuleHitCard(hit: RuleHit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (hit.severity == "SEVERE") MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.3f)
            else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
        ),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "${hit.drugA} ⟷ ${hit.drugB}",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold
                )
                SeverityBadge(hit.severity)
            }
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = hit.description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface
            )
        }
    }
}

@Composable
private fun SeverityBadge(severity: String) {
    val isSevere = severity == "SEVERE" || severity == "CRITICAL"
    val isWarning = severity == "WARNING" || severity == "MODERATE"
    val bgColor = when {
        isSevere -> MaterialTheme.colorScheme.error
        isWarning -> Color(0xFFF59E0B)
        else -> Color(0xFF10B981)
    }
    val label = when {
        isSevere -> "حرج"
        isWarning -> "تحذير"
        else -> "معلومات"
    }

    Surface(
        shape = RoundedCornerShape(6.dp),
        color = bgColor.copy(alpha = 0.15f)
    ) {
        Text(
            text = label,
            color = bgColor,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
        )
    }
}
