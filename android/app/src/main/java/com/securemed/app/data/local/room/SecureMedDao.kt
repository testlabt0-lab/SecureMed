package com.securemed.app.data.local.room

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Transaction

@Dao
interface SecureMedDao {
    // Patients
    @Query("SELECT * FROM patients")
    suspend fun getAllPatients(): List<PatientEntity>

    @Query("SELECT * FROM patients WHERE id = :id LIMIT 1")
    suspend fun getPatientById(id: String): PatientEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPatients(patients: List<PatientEntity>)

    @Query("DELETE FROM patients")
    suspend fun clearPatients()

    // Medical Records
    @Query("SELECT * FROM medical_records WHERE channelId = :channelId ORDER BY createdAt DESC")
    suspend fun getRecordsByChannel(channelId: String): List<MedicalRecordEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertRecords(records: List<MedicalRecordEntity>)

    @Query("DELETE FROM medical_records")
    suspend fun clearRecords()

    // Appointments
    @Query("DELETE FROM appointments")
    suspend fun clearAppointments()

    /**
     * Wipes every cached PHI table — used on logout, where the session's
     * patient data must not outlive the session. One transaction, so a
     * failure part-way through cannot leave half the cache behind, and
     * every table in the schema is covered: a wipe that skips one is a
     * silent data-retention bug.
     */
    @Transaction
    suspend fun clearAll() {
        clearPatients()
        clearRecords()
        clearAppointments()
    }
}
