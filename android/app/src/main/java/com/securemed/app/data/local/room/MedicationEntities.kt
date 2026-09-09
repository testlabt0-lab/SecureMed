package com.securemed.app.data.local.room

import androidx.room.Dao
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query

/**
 * Device-only medication plan — previously a row of a JSON list in
 * `LocalCache` (`medication_plans` key), now a real table.
 *
 * `times` is the one compound field: Room has no list column, and a side
 * table for dose times would buy nothing for a list that is always read
 * whole, so it is stored as a comma-joined string (times are HH:mm — a comma
 * can never appear inside one).
 *
 * Unlike the mirrored server entities in this database, these rows are NOT
 * refetchable: they are the durable copy of a device-first feature. That is
 * why the destructive-upgrade exemption below exists and why the migration
 * from the old JSON files matters.
 */
@Entity(tableName = "medication_plans")
data class MedicationPlanEntity(
    @PrimaryKey val id: String,
    val patientId: String,
    val patientName: String,
    val name: String,
    val dosage: String,
    /** HH:mm strings, comma-joined. */
    val times: String,
    val startDate: String,
    val endDate: String?,
    val instructions: String,
    val prescribedByName: String,
    val isActive: Boolean,
    val createdAt: String
) {
    companion object {
        fun joinTimes(times: List<String>): String = times.joinToString(",")
        fun splitTimes(joined: String): List<String> =
            joined.split(',').map { it.trim() }.filter { it.isNotEmpty() }
    }
}

/** One logged dose outcome — previously the `medication_dose_logs` JSON list. */
@Entity(tableName = "medication_dose_logs")
data class DoseLogEntity(
    @PrimaryKey val key: String,
    val planId: String,
    val date: String,
    val time: String,
    val status: String,
    val loggedAt: String
)

@Dao
interface MedicationDao {

    // ===== Plans =====

    @Query("SELECT * FROM medication_plans ORDER BY createdAt DESC")
    suspend fun getPlans(): List<MedicationPlanEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPlans(plans: List<MedicationPlanEntity>)

    @Query("DELETE FROM medication_plans")
    suspend fun deleteAllPlans()

    @Query("UPDATE medication_plans SET isActive = :active WHERE id = :planId")
    suspend fun setPlanActive(planId: String, active: Boolean)

    // ===== Dose logs =====

    @Query("SELECT * FROM medication_dose_logs")
    suspend fun getLogs(): List<DoseLogEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertLog(log: DoseLogEntity)

    @Query("DELETE FROM medication_dose_logs")
    suspend fun deleteAllLogs()
}
