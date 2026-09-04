package com.securemed.app.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class LabTestRequest(
    val id: String,
    val patient: String,
    @SerialName("patient_name") val patientName: String? = null,
    @SerialName("test_type") val testType: String,
    val status: String,
    val priority: String = "NORMAL",
    @SerialName("created_at") val createdAt: String
)

@Serializable
data class Appointment(
    val id: String,
    val patient: String,
    @SerialName("patient_name") val patientName: String? = null,
    val doctor: String,
    @SerialName("doctor_name") val doctorName: String? = null,
    @SerialName("appointment_date") val appointmentDate: String,
    val status: String,
    @SerialName("consultation_type") val consultationType: String,
    val notes: String? = null
)

@Serializable
data class TelemedicineSession(
    val id: String,
    val appointment: String,
    @SerialName("session_url") val sessionUrl: String? = null,
    val status: String,
    @SerialName("started_at") val startedAt: String? = null
)
