package com.securemed.app.widget

import android.content.Context
import android.content.Intent
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.Button
import androidx.glance.ButtonDefaults
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.GlanceTheme
import androidx.glance.action.actionStartActivity
import androidx.glance.action.clickable
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.appwidget.action.actionStartActivity
import androidx.glance.appwidget.cornerRadius
import androidx.glance.appwidget.provideContent
import androidx.glance.appwidget.updateAll
import androidx.glance.background
import androidx.glance.layout.Alignment
import androidx.glance.layout.Box
import androidx.glance.layout.Column
import androidx.glance.layout.Row
import androidx.glance.layout.Spacer
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.fillMaxWidth
import androidx.glance.layout.height
import androidx.glance.layout.padding
import androidx.glance.layout.width
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.ui.MainActivity

/**
 * Glance AppWidget displaying the doctor's today schedule and urgent quick actions.
 */
class DoctorScheduleGlanceWidget : GlanceAppWidget() {

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        provideContent {
            GlanceTheme {
                WidgetContent(context)
            }
        }
    }

    @Composable
    private fun WidgetContent(context: Context) {
        val isLoggedIn = SecurePreferences.isLoggedIn()
        val doctorName = SecurePreferences.userName ?: "د. المناوب"

        // Read cached widget data
        val remainingCount = SecurePreferences.remainingAppointmentsToday
        val nextPatient = SecurePreferences.nextPatientName ?: "لا يوجد مرضى حالياً"
        val nextTime = SecurePreferences.nextPatientTime ?: "--:--"

        val openAppIntent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        val scanBarcodeIntent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("extra_action", "scan_barcode")
        }

        val emergencyIntent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("extra_action", "break_glass")
        }

        Column(
            modifier = GlanceModifier
                .fillMaxSize()
                .background(ColorProvider(Color(0xFF0F172A)))
                .cornerRadius(16.dp)
                .padding(14.dp)
                .clickable(actionStartActivity(openAppIntent))
        ) {
            // Header: Doctor name and badge
            Row(
                modifier = GlanceModifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = GlanceModifier.defaultWeight()) {
                    Text(
                        text = "SecureMed • $doctorName",
                        style = TextStyle(
                            color = ColorProvider(Color(0xFF94A3B8)),
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium
                        )
                    )
                    Text(
                        text = if (isLoggedIn) "كشوفات اليوم المتبقية: $remainingCount" else "يرجى تسجيل الدخول",
                        style = TextStyle(
                            color = ColorProvider(Color.White),
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold
                        )
                    )
                }

                // Remaining badge
                Box(
                    modifier = GlanceModifier
                        .background(ColorProvider(Color(0xFF2563EB)))
                        .cornerRadius(8.dp)
                        .padding(horizontal = 8.dp, vertical = 4.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "$remainingCount",
                        style = TextStyle(
                            color = ColorProvider(Color.White),
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold
                        )
                    )
                }
            }

            Spacer(modifier = GlanceModifier.height(8.dp))

            // Next patient card
            Box(
                modifier = GlanceModifier
                    .fillMaxWidth()
                    .background(ColorProvider(Color(0xFF1E293B)))
                    .cornerRadius(10.dp)
                    .padding(8.dp)
            ) {
                Row(
                    modifier = GlanceModifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "👤 $nextPatient",
                        style = TextStyle(
                            color = ColorProvider(Color(0xFFE2E8F0)),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Medium
                        ),
                        modifier = GlanceModifier.defaultWeight()
                    )
                    Text(
                        text = "⏰ $nextTime",
                        style = TextStyle(
                            color = ColorProvider(Color(0xFF38BDF8)),
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold
                        )
                    )
                }
            }

            Spacer(modifier = GlanceModifier.defaultWeight())

            // Quick Action Buttons
            Row(
                modifier = GlanceModifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Button(
                    text = "📷 مسح باركود",
                    onClick = actionStartActivity(scanBarcodeIntent),
                    modifier = GlanceModifier.defaultWeight(),
                    colors = ButtonDefaults.buttonColors(
                        backgroundColor = ColorProvider(Color(0xFF0D9488)),
                        contentColor = ColorProvider(Color.White)
                    )
                )

                Spacer(modifier = GlanceModifier.width(8.dp))

                Button(
                    text = "🚨 طوارئ",
                    onClick = actionStartActivity(emergencyIntent),
                    modifier = GlanceModifier.defaultWeight(),
                    colors = ButtonDefaults.buttonColors(
                        backgroundColor = ColorProvider(Color(0xFFDC2626)),
                        contentColor = ColorProvider(Color.White)
                    )
                )
            }
        }
    }
}

class DoctorScheduleWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = DoctorScheduleGlanceWidget()
}

/**
 * Helper to update the widget data across the app.
 */
object WidgetDataUpdater {
    suspend fun updateWidget(
        context: Context,
        remainingCount: Int,
        nextPatient: String?,
        nextTime: String?
    ) {
        SecurePreferences.remainingAppointmentsToday = remainingCount
        SecurePreferences.nextPatientName = nextPatient
        SecurePreferences.nextPatientTime = nextTime
        DoctorScheduleGlanceWidget().updateAll(context)
    }
}
