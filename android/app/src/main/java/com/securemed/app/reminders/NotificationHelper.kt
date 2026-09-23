package com.securemed.app.reminders

import android.app.Notification
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
    const val CHANNEL_EMERGENCY = "emergency_alerts"
    const val CHANNEL_APPOINTMENTS = "appointment_reminders"
    const val CHANNEL_PUSH = "push_alerts"

    const val MEDICATION_NOTIFICATION_ID_BASE = 4200
    const val EMERGENCY_NOTIFICATION_ID_BASE = 9110
    const val APPOINTMENT_NOTIFICATION_ID_BASE = 6500

    /** Intent extra that makes MainActivity open the medications screen. */
    const val EXTRA_OPEN_MEDICATIONS = "open_medications"
    const val EXTRA_OPEN_APPOINTMENTS = "open_appointments"
    const val EXTRA_OPEN_PATIENT_ID = "open_patient_id"

    /**
     * Lock-screen stand-ins. A dose reminder names the drug, the dose and the
     * patient — PHI that must not be readable by whoever picks the phone up,
     * especially in an app that sets FLAG_SECURE on its own screens. These
     * carry no clinical detail.
     */
    private const val PUBLIC_TITLE = "⏰ تذكير بموعد دواء"
    private const val PUBLIC_TEXT = "افتح التطبيق لعرض التفاصيل"

    // No SDK_INT guard: minSdk is 26 (O), so notification channels are always
    // available. The guard that used to sit here could never be true, and lint
    // flagged it as ObsoleteSdkInt.
    fun ensureChannels(context: Context) {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        val medications = NotificationChannel(
            CHANNEL_MEDICATIONS,
            "تذكير الأدوية",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "تنبيهات مواعيد تناول الدواء"
            enableVibration(true)
            lockscreenVisibility = Notification.VISIBILITY_PRIVATE
        }
        manager.createNotificationChannel(medications)

        val emergency = NotificationChannel(
            CHANNEL_EMERGENCY,
            "🚨 تنبيهات الطوارئ والحالات الحرجة",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "تنبيهات طلبات Break-Glass وحالات الطوارئ الحرجة"
            enableVibration(true)
            vibrationPattern = longArrayOf(0, 500, 200, 500, 200, 800)
            lockscreenVisibility = Notification.VISIBILITY_PRIVATE
            setBypassDnd(true)
        }
        manager.createNotificationChannel(emergency)

        val appointments = NotificationChannel(
            CHANNEL_APPOINTMENTS,
            "مواعيد الكشف والعيادة",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "تنبيهات مواعيد الكشف القادمة بدون إنترنت"
            enableVibration(true)
            lockscreenVisibility = Notification.VISIBILITY_PRIVATE
        }
        manager.createNotificationChannel(appointments)
    }

    /** True when the device allows posting notifications. */
    fun canNotify(context: Context): Boolean =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            context.checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) ==
                PackageManager.PERMISSION_GRANTED
        } else {
            NotificationManagerCompat.from(context).areNotificationsEnabled()
        }

    fun showNotification(context: Context, title: String, body: String) {
        ensureChannels(context)
        ensurePushChannel(context)

        val openApp = PendingIntent.getActivity(
            context,
            (title.hashCode() + body.hashCode()),
            Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(context, CHANNEL_PUSH)
            .setSmallIcon(R.drawable.ic_medication)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setAutoCancel(true)
            .setContentIntent(openApp)
            // Push carries clinical summaries; the lock screen gets the bare
            // existence signal, exactly like medication reminders.
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
            .setPublicVersion(
                NotificationCompat.Builder(context, CHANNEL_PUSH)
                    .setSmallIcon(R.drawable.ic_medication)
                    .setContentTitle("إشعار من SecureMed")
                    .setContentText("افتح التطبيق لعرض التفاصيل")
                    .setCategory(NotificationCompat.CATEGORY_MESSAGE)
                    .setAutoCancel(true)
                    .setContentIntent(openApp)
                    .build()
            )
            .build()

        try {
            NotificationManagerCompat.from(context).notify(title.hashCode(), notification)
        } catch (_: SecurityException) {
        }
    }

    private fun ensurePushChannel(context: Context) {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channel = NotificationChannel(
            CHANNEL_PUSH,
            "الإشعارات الفورية",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "تنبيهات النظام الطبية والأمنية الفورية"
            enableVibration(true)
            lockscreenVisibility = Notification.VISIBILITY_PRIVATE
        }
        manager.createNotificationChannel(channel)
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
                putExtra(EXTRA_OPEN_MEDICATIONS, true)
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
            // Full text only once the device is unlocked; the public version
            // is what a locked screen shows instead.
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
            .setPublicVersion(
                NotificationCompat.Builder(context, CHANNEL_MEDICATIONS)
                    .setSmallIcon(R.drawable.ic_medication)
                    .setContentTitle(PUBLIC_TITLE)
                    .setContentText(PUBLIC_TEXT)
                    .setCategory(NotificationCompat.CATEGORY_REMINDER)
                    .setAutoCancel(true)
                    .setContentIntent(openApp)
                    .build()
            )
            .build()

        try {
            NotificationManagerCompat.from(context).notify(notificationId, notification)
        } catch (_: SecurityException) {
            // POST_NOTIFICATIONS revoked — silently ignore.
        }
    }

    /**
     * Urgent Heads-up Emergency Alert (Break-Glass / Critical Patient).
     * Bypasses DND with strong vibration and priority MAX.
     */
    fun showEmergencyAlert(
        context: Context,
        title: String,
        message: String,
        patientId: String? = null
    ) {
        ensureChannels(context)

        val notificationId = EMERGENCY_NOTIFICATION_ID_BASE + (title.hashCode() and 0x7FFFFFFF) % 1000

        val openApp = PendingIntent.getActivity(
            context,
            notificationId,
            Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                putExtra("extra_action", "break_glass")
                if (!patientId.isNullOrBlank()) {
                    putExtra(EXTRA_OPEN_PATIENT_ID, patientId)
                }
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(context, CHANNEL_EMERGENCY)
            .setSmallIcon(R.drawable.ic_shortcut_emergency)
            .setColor(0xFFDC2626.toInt()) // Red alert
            .setContentTitle("🚨 $title")
            .setContentText(message)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message))
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setAutoCancel(true)
            .setContentIntent(openApp)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .addAction(
                R.drawable.ic_shortcut_emergency,
                "فتح الحالة فوراً",
                openApp
            )
            .build()

        try {
            NotificationManagerCompat.from(context).notify(notificationId, notification)
        } catch (_: SecurityException) {
        }
    }

    /**
     * Offline Appointment Reminder notification scheduled via AlarmManager.
     */
    fun showAppointmentReminder(
        context: Context,
        patientName: String,
        doctorName: String,
        timeText: String,
        appointmentId: String
    ) {
        ensureChannels(context)

        val notificationId = APPOINTMENT_NOTIFICATION_ID_BASE + (appointmentId.hashCode() and 0x7FFFFFFF) % 1000

        val openApp = PendingIntent.getActivity(
            context,
            notificationId,
            Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                putExtra(EXTRA_OPEN_APPOINTMENTS, true)
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val title = "📅 تذكير بموعد كشف طبي — $timeText"
        val message = "موعد للمريض: $patientName مع د. $doctorName"

        val notification = NotificationCompat.Builder(context, CHANNEL_APPOINTMENTS)
            .setSmallIcon(R.drawable.ic_shortcut_add_patient)
            .setColor(0xFF2563EB.toInt())
            .setContentTitle(title)
            .setContentText(message)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_EVENT)
            .setAutoCancel(true)
            .setContentIntent(openApp)
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
            .build()

        try {
            NotificationManagerCompat.from(context).notify(notificationId, notification)
        } catch (_: SecurityException) {
        }
    }
}

