package com.securemed.app.data.local

import com.securemed.app.data.local.room.DoseLogEntity
import com.securemed.app.data.local.room.MedicationDao
import com.securemed.app.data.local.room.MedicationPlanEntity
import com.securemed.app.data.model.AdherenceStats
import com.securemed.app.data.model.Medication
import com.securemed.app.data.model.MedicationDoseLog
import com.securemed.app.data.model.TodayDose
import com.securemed.app.data.model.TodayDosesResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withContext
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.json.Json
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime
import java.time.format.DateTimeFormatter

/**
 * Device-local store for medication plans and dose logs, persisted in the
 * encrypted Room database ([MedicationPlanEntity] / [DoseLogEntity] via
 * [MedicationDao]) since 3-4 — previously a JSON list per key in
 * [LocalCache].
 *
 * The migration story: a device upgrading from a build before 3-4 still has
 * its plans/logs in `LocalCache`'s encrypted files. [migrateFromLocalCache]
 * runs once at startup (before any destructive database fallback could run
 * away with them), imports the rows into Room, and only then deletes the
 * files. From that point on Room is the single home for device-only data and
 * `LocalCache` no longer participates at all (it still backs the server-mirror
 * reads until their owners move, which is why its init stays).
 *
 * Every data function is `suspend` and hops to [Dispatchers.IO]: SQLCipher
 * adds real crypto latency to each Room query, and these were called from
 * the Main dispatcher by the medications/dashboard view models — a blocking
 * encrypted read on the UI thread, i.e. a jank/ANR factory. The one
 * deliberate exception is [migrateFromLocalCache], which stays synchronous:
 * Application.onCreate must finish it before the database is ever opened,
 * and a fire-and-forget migration would race the first DAO use on an
 * upgrading device (see [com.securemed.app.di.DatabaseModule]).
 */
object MedicationStore {

    private const val PLANS_KEY = "medication_plans"
    private const val LOGS_KEY = "medication_dose_logs"

    const val STATUS_TAKEN = "TAKEN"
    const val STATUS_SKIPPED = "SKIPPED"
    const val STATUS_MISSED = "MISSED"
    const val STATUS_PENDING = "PENDING"

    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }

    private var dao: MedicationDao? = null

    /** Call once from SecureMedApp.onCreate() before anything reads plans. */
    fun init(medicationDao: MedicationDao) {
        dao = medicationDao
    }

    // ===== Migration (3-4): encrypted JSON files → Room, once =====

    /**
     * Imports the legacy JSON files into Room and removes them. Idempotent by
     * construction: files are deleted after a successful import, and an empty
     * or unreadable file yields empty lists — importing nothing and deleting
     * nothing is the same no-op.
     *
     * Synchronous by design — see the class KDoc. The I/O itself runs on
     * [Dispatchers.IO]; `runBlocking` here only means "Application.onCreate
     * waits for this", which is the ordering guarantee the migration exists
     * to provide.
     */
    fun migrateFromLocalCache() {
        val target = dao ?: return
        runBlocking(Dispatchers.IO) {
            val plans = runCatching {
                LocalCache.load(PLANS_KEY)?.let { raw ->
                    json.decodeFromString(ListSerializer(Medication.serializer()), raw)
                } ?: emptyList()
            }.getOrDefault(emptyList())
            val logs = runCatching {
                LocalCache.load(LOGS_KEY)?.let { raw ->
                    json.decodeFromString(ListSerializer(MedicationDoseLog.serializer()), raw)
                } ?: emptyList()
            }.getOrDefault(emptyList())

            if (plans.isNotEmpty()) {
                target.insertPlans(plans.map { it.toEntity() })
                LocalCache.delete(PLANS_KEY)
            }
            if (logs.isNotEmpty()) {
                logs.forEach { log ->
                    target.insertLog(
                        DoseLogEntity(
                            key = log.key,
                            planId = log.planId,
                            date = log.date,
                            time = log.time,
                            status = log.status,
                            loggedAt = log.loggedAt
                        )
                    )
                }
                LocalCache.delete(LOGS_KEY)
            }
        }
    }

    private fun Medication.toEntity() = MedicationPlanEntity(
        id = id,
        patientId = patientId,
        patientName = patientName,
        name = name,
        dosage = dosage,
        times = MedicationPlanEntity.joinTimes(times),
        startDate = startDate,
        endDate = endDate,
        instructions = instructions,
        prescribedByName = prescribedByName,
        isActive = isActive,
        createdAt = createdAt
    )

    private fun MedicationPlanEntity.toModel() = Medication(
        id = id,
        patientId = patientId,
        patientName = patientName,
        name = name,
        dosage = dosage,
        times = MedicationPlanEntity.splitTimes(times),
        startDate = startDate,
        endDate = endDate,
        instructions = instructions,
        prescribedByName = prescribedByName,
        isActive = isActive,
        createdAt = createdAt
    )

    private fun DoseLogEntity.toModel() = MedicationDoseLog(
        key = key,
        planId = planId,
        date = date,
        time = time,
        status = status,
        loggedAt = loggedAt
    )

    // ===== Plans =====

    suspend fun loadPlans(): List<Medication> = withContext(Dispatchers.IO) {
        val target = dao ?: return@withContext emptyList()
        runCatching { target.getPlans().map { it.toModel() } }.getOrDefault(emptyList())
    }

    suspend fun savePlans(plans: List<Medication>) = withContext(Dispatchers.IO) {
        val target = dao ?: return@withContext
        runCatching {
            target.deleteAllPlans()
            target.insertPlans(plans.map { it.toEntity() })
        }
    }

    suspend fun addPlan(plan: Medication) = withContext(Dispatchers.IO) {
        val target = dao ?: return@withContext
        runCatching { target.insertPlans(listOf(plan.toEntity())) }
    }

    suspend fun setPlanActive(planId: String, active: Boolean) = withContext(Dispatchers.IO) {
        val target = dao ?: return@withContext
        runCatching { target.setPlanActive(planId, active) }
    }

    // ===== Dose logs =====

    suspend fun loadLogs(): List<MedicationDoseLog> = withContext(Dispatchers.IO) {
        val target = dao ?: return@withContext emptyList()
        runCatching { target.getLogs().map { it.toModel() } }.getOrDefault(emptyList())
    }

    suspend fun logDose(planId: String, scheduledFor: String, status: String): MedicationDoseLog =
        withContext(Dispatchers.IO) {
            val parts = scheduledFor.split("T")
            val entry = MedicationDoseLog(
                key = "$planId|$scheduledFor",
                planId = planId,
                date = parts.getOrNull(0) ?: LocalDate.now().toString(),
                time = parts.getOrNull(1)?.take(5) ?: LocalTime.now().toString().take(5),
                status = status,
                loggedAt = LocalDateTime.now().toString()
            )
            val target = dao
            if (target != null) {
                // REPLACE on the primary key is the "one row per plan+slot" rule
                // the old read-filter-write JSON dance enforced.
                runCatching { target.insertLog(entry.toLogEntity()) }
            }
            entry
        }

    private fun MedicationDoseLog.toLogEntity() = DoseLogEntity(
        key = key,
        planId = planId,
        date = date,
        time = time,
        status = status,
        loggedAt = loggedAt
    )

    // ===== Derived views =====

    /** Today's doses across all active plans, with live status per dose. */
    suspend fun todayDoses(today: LocalDate = LocalDate.now()): List<TodayDose> {
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

    suspend fun todayDosesResponse(): TodayDosesResponse = TodayDosesResponse(todayDoses())

    /** Adherence over the last [days] days from local dose logs. */
    suspend fun adherenceStats(days: Int = 7): AdherenceStats {
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
