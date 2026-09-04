package com.securemed.app.data.local.room

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Local representation of a Patient.
 */
@Entity(tableName = "patients")
data class PatientEntity(
    @PrimaryKey val id: String,
    val fullName: String,
    val dateOfBirth: String,
    val gender: String,
    val bloodType: String?,
    val age: Int?,
    val phone: String?,
    val chronicConditions: String?
)

/**
 * Local representation of a Medical Record.
 */
@Entity(tableName = "medical_records")
data class MedicalRecordEntity(
    @PrimaryKey val id: String,
    val channelId: String?,
    val title: String,
    val content: String,
    val recordType: String,
    val recordTypeDisplay: String,
    val createdByName: String,
    val isCritical: Boolean,
    val createdAt: String
)

/**
 * Local representation of an Appointment.
 */
@Entity(tableName = "appointments")
data class AppointmentEntity(
    @PrimaryKey val id: String,
    val patientId: String,
    val providerId: String,
    val scheduledTime: String,
    val type: String,
    val status: String
)
