package com.securemed.app.reminders

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.securemed.app.R
import com.securemed.app.ui.MainActivity

/**
 * Medication reminder notifications (system-level, fire even when the
 * app is closed).
 */
object NotificationHelper {

    const val CHANNEL_MEDICATIONS = "medication_reminders"
    const val MEDICATION_NOTIFICATION_ID_BASE = 4200

    fun ensureChannels(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        val medications = NotificationChannel(
            CHANNEL_MEDICATIONS,
            "تذكير الأدوية",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "تنبيهات مواعيد تناول الدواء"
            enableVibration(true)
        }
        manager.createNotificationChannel(medications)
    }

    /** True when the device allows posting notifications. */
    fun canNotify(context: Context): Boolean =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            context.checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) ==
                PackageManager.PERMISSION_GRANTED
        } else {
            NotificationManagerCompat.from(context).areNotificationsEnabled()
        }

    fun showMedicationReminder(
        context: Context,
        medicationName: String,
        dosage: String,
        patientName: String,
        instructions: String,
        timeText: String,
        notificationId: Int
    ) {
        ensureChannels(context)

        val openApp = PendingIntent.getActivity(
            context,
            notificationId,
            Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                putExtra("open_medications", true)
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val title = "⏰ وقت تناول الدواء — $timeText"
        val text = buildString {
            append("$medicationName ($dosage)")
            if (patientName.isNotBlank()) append(" — $patientName")
            if (instructions.isNotBlank()) append("\n$instructions")
        }

        val notification = NotificationCompat.Builder(context, CHANNEL_MEDICATIONS)
            .setSmallIcon(R.drawable.ic_medication)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_REMINDER)
            .setAutoCancel(true)
            .setContentIntent(openApp)
            .build()

        try {
            NotificationManagerCompat.from(context).notify(notificationId, notification)
        } catch (_: SecurityException) {
            // POST_NOTIFICATIONS revoked — silently ignore.
        }
    }
}
