package com.securemed.app.reminders

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import com.securemed.app.data.local.LocalCache
import com.securemed.app.data.model.Medication
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.json.Json
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/**
 * Schedules system alarms for the next upcoming dose of every active
 * medication. One alarm per medication (requestCode = medication hash);
 * when it fires, [ReminderReceiver] shows the notification and asks the
 * scheduler to queue the following dose.
 *
 * The medication list is mirrored into the offline disk cache by the
 * repository, so scheduling also works offline and after reboot
 * (see [BootReceiver]).
 */
class ReminderScheduler(private val context: Context) {

    companion object {
        const val EXTRA_MEDICATION_NAME = "med_name"
        const val EXTRA_MEDICATION_DOSAGE = "med_dosage"
        const val EXTRA_PATIENT_NAME = "patient_name"
        const val EXTRA_INSTRUCTIONS = "med_instructions"
        const val EXTRA_TIME_TEXT = "time_text"
        const val EXTRA_MEDICATION_ID = "med_id"

        private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }
    }

    private val alarmManager =
        context.getSystemService(Context.ALARM_SERVICE) as AlarmManager

    /** Load cached medications and (re)schedule every active one. */
    fun refreshFromCache() {
        val raw = LocalCache.load("medications") ?: return
        val medications = try {
            json.decodeFromString(ListSerializer(Medication.serializer()), raw)
        } catch (_: Exception) {
            return
        }
        medications
            .filter { it.isActive && it.times.isNotEmpty() }
            .forEach { scheduleNext(it) }
    }

    /**
     * Schedule the alarm for the medication's next upcoming dose
     * (today's remaining times, else tomorrow's first dose).
     */
    fun scheduleNext(medication: Medication) {
        val next = nextDose(medication) ?: run {
            cancel(medication.id)
            return
        }

        val intent = Intent(context, ReminderReceiver::class.java).apply {
            action = "com.securemed.app.MEDICATION_REMINDER"
            putExtra(EXTRA_MEDICATION_ID, medication.id)
            putExtra(EXTRA_MEDICATION_NAME, medication.name)
            putExtra(EXTRA_MEDICATION_DOSAGE, medication.dosage)
            putExtra(EXTRA_PATIENT_NAME, medication.patientName)
            putExtra(EXTRA_INSTRUCTIONS, medication.instructions)
            putExtra(EXTRA_TIME_TEXT, next.second.format(TIME_FORMAT))
        }

        val requestCode = medication.id.hashCode()
        val pending = PendingIntent.getBroadcast(
            context,
            requestCode,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val triggerAtMillis = next.first
            .atZone(ZoneId.systemDefault())
            .toInstant()
            .toEpochMilli()

        // Exact alarms need the user-granted permission on Android 12+;
        // fall back to an inexact window (drift is acceptable for meds).
        val exactAllowed = Build.VERSION.SDK_INT < Build.VERSION_CODES.S ||
            alarmManager.canScheduleExactAlarms()

        if (exactAllowed) {
            alarmManager.setExactAndAllowWhileIdle(
                AlarmManager.RTC_WAKEUP, triggerAtMillis, pending
            )
        } else {
            alarmManager.setWindow(
                AlarmManager.RTC_WAKEUP, triggerAtMillis,
                10 * 60 * 1000L, pending
            )
        }
    }

    fun cancel(medicationId: String) {
        val pending = PendingIntent.getBroadcast(
            context,
            medicationId.hashCode(),
            Intent(context, ReminderReceiver::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        alarmManager.cancel(pending)
    }

    /** Next (triggerMillis, time-of-day) pair for this medication. */
    private fun nextDose(medication: Medication): Pair<LocalDateTime, LocalTime>? {
        val now = LocalDateTime.now()
        val today = LocalDate.now()

        val times = medication.times
            .mapNotNull { runCatching { LocalTime.parse(it) }.getOrNull() }
            .sorted()

        if (times.isEmpty()) return null

        // Active window check: start/end dates
        val start = runCatching { LocalDate.parse(medication.startDate) }.getOrNull()
        val end = medication.endDate?.let { runCatching { LocalDate.parse(it) }.getOrNull() }

        for (day in listOf(today, today.plusDays(1))) {
            if (start != null && day.isBefore(start)) continue
            if (end != null && day.isAfter(end)) continue
            for (time in times) {
                val moment = LocalDateTime.of(day, time)
                if (moment.isAfter(now)) return moment to time
            }
        }
        return null
    }

    private val TIME_FORMAT: DateTimeFormatter = DateTimeFormatter.ofPattern("HH:mm")
}

/**
 * Fires when a medication alarm triggers: posts the notification and
 * queues the next dose for that medication.
 */
class ReminderReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != "com.securemed.app.MEDICATION_REMINDER") return

        NotificationHelper.ensureChannels(context)

        val medicationId = intent.getStringExtra(ReminderScheduler.EXTRA_MEDICATION_ID) ?: return
        val notificationId = NotificationHelper.MEDICATION_NOTIFICATION_ID_BASE +
            (medicationId.hashCode() and 0x7FFFFFFF) % 10000

        NotificationHelper.showMedicationReminder(
            context = context,
            medicationName = intent.getStringExtra(ReminderScheduler.EXTRA_MEDICATION_NAME) ?: "دواء",
            dosage = intent.getStringExtra(ReminderScheduler.EXTRA_MEDICATION_DOSAGE) ?: "",
            patientName = intent.getStringExtra(ReminderScheduler.EXTRA_PATIENT_NAME) ?: "",
            instructions = intent.getStringExtra(ReminderScheduler.EXTRA_INSTRUCTIONS) ?: "",
            timeText = intent.getStringExtra(ReminderScheduler.EXTRA_TIME_TEXT) ?: "",
            notificationId = notificationId
        )

        // Queue the following dose from the cached plan
        try {
            ReminderScheduler(context).refreshFromCache()
        } catch (_: Exception) {
        }
    }
}

/**
 * Re-arms all medication alarms after a device reboot (alarms are
 * cleared by the system on shutdown).
 */
class BootReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        try {
            ReminderScheduler(context).refreshFromCache()
        } catch (_: Exception) {
        }
    }
}
