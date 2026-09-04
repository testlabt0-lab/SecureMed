package com.securemed.app.data.local

import com.securemed.app.data.model.AdherenceStats
import com.securemed.app.data.model.Medication
import com.securemed.app.data.model.MedicationDoseLog
import com.securemed.app.data.model.TodayDose
import com.securemed.app.data.model.TodayDosesResponse
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.json.Json
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime
import java.time.format.DateTimeFormatter

/**
 * Device-local store for medication plans and dose logs, persisted through
 * [LocalCache] (app-private storage, cleared on logout).
 *
 * The backend has no dose-plan endpoint, so plans are a first-class offline
 * feature: clinicians create them here, alarms are scheduled by
 * [com.securemed.app.reminders.ReminderScheduler], and adherence is computed
 * from the logs on this device.
 */
object MedicationStore {

    private const val PLANS_KEY = "medication_plans"
    private const val LOGS_KEY = "medication_dose_logs"

    const val STATUS_TAKEN = "TAKEN"
    const val STATUS_SKIPPED = "SKIPPED"
    const val STATUS_MISSED = "MISSED"
    const val STATUS_PENDING = "PENDING"

    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }

    // ===== Plans =====

    @Synchronized
    fun loadPlans(): List<Medication> {
        val raw = LocalCache.load(PLANS_KEY) ?: return emptyList()
        return try {
            json.decodeFromString(ListSerializer(Medication.serializer()), raw)
        } catch (_: Exception) {
            emptyList()
        }
    }

    @Synchronized
    fun savePlans(plans: List<Medication>) {
        LocalCache.save(PLANS_KEY, json.encodeToString(ListSerializer(Medication.serializer()), plans))
    }

    fun addPlan(plan: Medication) {
        savePlans(loadPlans() + plan)
    }

    fun setPlanActive(planId: String, active: Boolean) {
        savePlans(loadPlans().map { if (it.id == planId) it.copy(isActive = active) else it })
    }

    // ===== Dose logs =====

    @Synchronized
    fun loadLogs(): List<MedicationDoseLog> {
        val raw = LocalCache.load(LOGS_KEY) ?: return emptyList()
        return try {
            json.decodeFromString(ListSerializer(MedicationDoseLog.serializer()), raw)
        } catch (_: Exception) {
            emptyList()
        }
    }

    @Synchronized
    fun logDose(planId: String, scheduledFor: String, status: String): MedicationDoseLog {
        val parts = scheduledFor.split("T")
        val entry = MedicationDoseLog(
            key = "$planId|$scheduledFor",
            planId = planId,
            date = parts.getOrNull(0) ?: LocalDate.now().toString(),
            time = parts.getOrNull(1)?.take(5) ?: LocalTime.now().toString().take(5),
            status = status,
            loggedAt = LocalDateTime.now().toString()
        )
        val others = loadLogs().filter { it.key != entry.key }
        saveLogs(others + entry)
        return entry
    }

    private fun saveLogs(logs: List<MedicationDoseLog>) {
        LocalCache.save(LOGS_KEY, json.encodeToString(ListSerializer(MedicationDoseLog.serializer()), logs))
    }

    // ===== Derived views =====

    /** Today's doses across all active plans, with live status per dose. */
    fun todayDoses(today: LocalDate = LocalDate.now()): List<TodayDose> {
        val now = LocalDateTime.now()
        val logs = loadLogs().associateBy { it.key }
        val doses = mutableListOf<TodayDose>()

        loadPlans().filter { it.isActive }.forEach { plan ->
            val start = runCatching { LocalDate.parse(plan.startDate) }.getOrNull()
            val end = plan.endDate?.let { runCatching { LocalDate.parse(it) }.getOrNull() }
            if (start != null && today.isBefore(start)) return@forEach
            if (end != null && today.isAfter(end)) return@forEach

            plan.times.forEach { rawTime ->
                val time = runCatching { LocalTime.parse(rawTime) }.getOrNull() ?: return@forEach
                val scheduledFor = LocalDateTime.of(today, time)
                val key = "${plan.id}|$scheduledFor"
                val status = when {
                    logs[key]?.status == STATUS_TAKEN -> STATUS_TAKEN
                    logs[key]?.status == STATUS_SKIPPED -> STATUS_SKIPPED
                    scheduledFor.isBefore(now) -> STATUS_MISSED
                    else -> STATUS_PENDING
                }
                doses += TodayDose(
                    medicationId = plan.id,
                    medicationName = plan.name,
                    dosage = plan.dosage,
                    patientName = plan.patientName,
                    time = time.format(DateTimeFormatter.ofPattern("HH:mm")),
                    scheduledFor = scheduledFor.toString(),
                    status = status,
                    instructions = plan.instructions
                )
            }
        }
        return doses.sortedBy { it.scheduledFor }
    }

    fun todayDosesResponse(): TodayDosesResponse = TodayDosesResponse(todayDoses())

    /** Adherence over the last [days] days from local dose logs. */
    fun adherenceStats(days: Int = 7): AdherenceStats {
        val today = LocalDate.now()
        val takenKeys = loadLogs()
            .filter { it.status == STATUS_TAKEN }
            .map { it.key }
            .toSet()
        var expected = 0
        var taken = 0

        loadPlans().filter { it.isActive }.forEach { plan ->
            val start = runCatching { LocalDate.parse(plan.startDate) }.getOrNull()
            val end = plan.endDate?.let { runCatching { LocalDate.parse(it) }.getOrNull() }
            for (offset in days - 1 downTo 0) {
                val day = today.minusDays(offset.toLong())
                if (start != null && day.isBefore(start)) continue
                if (end != null && day.isAfter(end)) continue
                plan.times.forEach { rawTime ->
                    val time = runCatching { LocalTime.parse(rawTime) }.getOrNull() ?: return@forEach
                    expected++
                    if ("${plan.id}|${LocalDateTime.of(day, time)}" in takenKeys) taken++
                }
            }
        }

        val percent = if (expected == 0) 0 else (taken * 100) / expected
        return AdherenceStats(totalDoses = expected, takenDoses = taken, adherencePercent = percent)
    }
}
