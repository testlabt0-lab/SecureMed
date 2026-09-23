package com.securemed.app.ui.components

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import com.securemed.app.data.model.Patient

@Composable
fun EmergencyMedicalCardDialog(
    patient: Patient,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    var selectedTab by remember { mutableStateOf(0) } // 0: Emergency Card, 1: Wristband

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            shape = RoundedCornerShape(24.dp),
            color = MaterialTheme.colorScheme.surface,
            tonalElevation = 6.dp,
            modifier = Modifier
                .fillMaxWidth()
                .padding(4.dp)
        ) {
            Column(
                modifier = Modifier
                    .padding(20.dp)
                    .verticalScroll(rememberScrollState()),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                // Header with Close
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(36.dp)
                                .clip(CircleShape)
                                .background(Color(0xFFDC2626)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                Icons.Default.MedicalServices,
                                contentDescription = null,
                                tint = Color.White,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                        Spacer(modifier = Modifier.width(10.dp))
                        Text(
                            text = if (selectedTab == 0) "بطاقة الطوارئ الطبية" else "سوار معصم المريض",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    IconButton(onClick = onDismiss) {
                        Icon(Icons.Default.Close, contentDescription = "إغلاق")
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Tab Switcher
                TabRow(
                    selectedTabIndex = selectedTab,
                    modifier = Modifier.clip(RoundedCornerShape(12.dp)),
                    containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
                    indicator = {},
                    divider = {}
                ) {
                    Tab(
                        selected = selectedTab == 0,
                        onClick = { selectedTab = 0 },
                        text = { Text("بطاقة الطوارئ") },
                        icon = { Icon(Icons.Default.Badge, contentDescription = null, modifier = Modifier.size(18.dp)) }
                    )
                    Tab(
                        selected = selectedTab == 1,
                        onClick = { selectedTab = 1 },
                        text = { Text("سوار المعصم (QR)") },
                        icon = { Icon(Icons.Default.QrCode, contentDescription = null, modifier = Modifier.size(18.dp)) }
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                if (selectedTab == 0) {
                    // ===== EMERGENCY CR80 CARD VIEW =====
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(
                                width = 2.dp,
                                brush = Brush.horizontalGradient(
                                    listOf(Color(0xFFDC2626), Color(0xFFEF4444))
                                ),
                                shape = RoundedCornerShape(18.dp)
                            ),
                        shape = RoundedCornerShape(18.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surface
                        )
                    ) {
                        Column {
                            // Top Red Header
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .background(
                                        Brush.horizontalGradient(
                                            listOf(Color(0xFFB91C1C), Color(0xFFDC2626))
                                        )
                                    )
                                    .padding(horizontal = 16.dp, vertical = 10.dp)
                            ) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(
                                            Icons.Default.Emergency,
                                            contentDescription = null,
                                            tint = Color.White,
                                            modifier = Modifier.size(20.dp)
                                        )
                                        Spacer(modifier = Modifier.width(8.dp))
                                        Text(
                                            text = "EMERGENCY MEDICAL ID",
                                            color = Color.White,
                                            style = MaterialTheme.typography.labelMedium,
                                            fontWeight = FontWeight.ExtraBold,
                                            fontFamily = FontFamily.Monospace
                                        )
                                    }
                                    Text(
                                        text = "SecureMed",
                                        color = Color.White.copy(alpha = 0.85f),
                                        style = MaterialTheme.typography.labelSmall,
                                        fontWeight = FontWeight.Bold
                                    )
                                }
                            }

                            // Card Body
                            Column(modifier = Modifier.padding(16.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.Top
                                ) {
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(
                                            text = patient.fullName,
                                            style = MaterialTheme.typography.titleLarge,
                                            fontWeight = FontWeight.Black
                                        )
                                        Text(
                                            text = "العمر: ${patient.age ?: "غير محدد"} سنة • ${if (patient.gender == "M") "ذكر" else "أنثى"}",
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }

                                    // Blood Type Badge
                                    Surface(
                                        shape = RoundedCornerShape(10.dp),
                                        color = Color(0xFFDC2626),
                                        modifier = Modifier.padding(start = 8.dp)
                                    ) {
                                        Column(
                                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                                            horizontalAlignment = Alignment.CenterHorizontally
                                        ) {
                                            Text(
                                                text = "فصيلة الدم",
                                                color = Color.White.copy(alpha = 0.8f),
                                                style = MaterialTheme.typography.labelSmall
                                            )
                                            Text(
                                                text = patient.bloodType ?: "؟",
                                                color = Color.White,
                                                style = MaterialTheme.typography.titleMedium,
                                                fontWeight = FontWeight.Black
                                            )
                                        }
                                    }
                                }

                                Spacer(modifier = Modifier.height(12.dp))

                                // Chronic conditions & Allergies
                                if (!patient.chronicConditions.isNullOrBlank()) {
                                    Surface(
                                        shape = RoundedCornerShape(8.dp),
                                        color = MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.4f),
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        Row(
                                            modifier = Modifier.padding(10.dp),
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Icon(
                                                Icons.Default.Warning,
                                                contentDescription = null,
                                                tint = Color(0xFFDC2626),
                                                modifier = Modifier.size(18.dp)
                                            )
                                            Spacer(modifier = Modifier.width(8.dp))
                                            Column {
                                                Text(
                                                    text = "حالات وحساسيات حرجة:",
                                                    style = MaterialTheme.typography.labelSmall,
                                                    fontWeight = FontWeight.Bold,
                                                    color = Color(0xFFB91C1C)
                                                )
                                                Text(
                                                    text = patient.chronicConditions,
                                                    style = MaterialTheme.typography.bodySmall,
                                                    color = MaterialTheme.colorScheme.onSurface
                                                )
                                            }
                                        }
                                    }
                                    Spacer(modifier = Modifier.height(10.dp))
                                }

                                // Phone Call button
                                if (!patient.phone.isNullOrBlank()) {
                                    OutlinedButton(
                                        onClick = {
                                            val dialIntent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:${patient.phone}"))
                                            context.startActivity(dialIntent)
                                        },
                                        modifier = Modifier.fillMaxWidth(),
                                        shape = RoundedCornerShape(10.dp)
                                    ) {
                                        Icon(Icons.Default.Phone, contentDescription = null, modifier = Modifier.size(18.dp))
                                        Spacer(modifier = Modifier.width(8.dp))
                                        Text("اتصال بالطوارئ: ${patient.phone}")
                                    }
                                }
                            }
                        }
                    }
                } else {
                    // ===== WRISTBAND VIEW =====
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(
                                1.dp,
                                MaterialTheme.colorScheme.outlineVariant,
                                RoundedCornerShape(16.dp)
                            ),
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f)
                        )
                    ) {
                        Column(
                            modifier = Modifier.padding(16.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Text(
                                text = "سوار المعصم الطبي للمريض",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "يُستخدم للتحقق السريري عند السرير والفرز الفوري",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )

                            Spacer(modifier = Modifier.height(14.dp))

                            // Simulated QR / Barcode Canvas Box
                            Box(
                                modifier = Modifier
                                    .size(160.dp)
                                    .clip(RoundedCornerShape(16.dp))
                                    .background(Color.White)
                                    .border(2.dp, Color.Black, RoundedCornerShape(16.dp))
                                    .padding(12.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                    Icon(
                                        Icons.Default.QrCode2,
                                        contentDescription = "QR Code",
                                        tint = Color.Black,
                                        modifier = Modifier.size(100.dp)
                                    )
                                    Text(
                                        text = patient.id.take(8).uppercase(),
                                        fontFamily = FontFamily.Monospace,
                                        style = MaterialTheme.typography.labelSmall,
                                        color = Color.Black,
                                        fontWeight = FontWeight.Bold
                                    )
                                }
                            }

                            Spacer(modifier = Modifier.height(12.dp))

                            Text(
                                text = patient.fullName,
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Black
                            )
                            Text(
                                text = "MRN: ${patient.id.take(8)} • فصيلة: ${patient.bloodType ?: "غير محدد"}",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.outline
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                Button(
                    onClick = onDismiss,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("تم")
                }
            }
        }
    }
}
