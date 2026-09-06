package com.securemed.app.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * A lab order — `GET lab/orders/` (`LabOrderSerializer`).
 *
 * The client used to call `lab/requests/`, a route that does not exist, and to
 * expect a `test_type` field the serializer never produced: the test is
 * flattened as `test_name`/`test_category`. Every field except [id] therefore
 * carries a default, so one renamed column on the server degrades a single
 * label instead of failing the whole list.
 */
@Serializable
data class LabTestRequest(
    val id: String,
    val patient: String = "",
    @SerialName("patient_name") val patientName: String? = null,
    @SerialName("test_name") val testName: String? = null,
    @SerialName("test_category") val testCategory: String? = null,
    @SerialName("doctor_name") val doctorName: String? = null,
    val status: String = "",
    val priority: String = "NORMAL",
    @SerialName("clinical_notes") val clinicalNotes: String? = null,
    @SerialName("created_at") val createdAt: String = ""
)

/**
 * An appointment — `GET appointments/` (`AppointmentSerializer`).
 *
 * The previous shape asked for `appointment_date` and `consultation_type`;
 * the server sends `scheduled_at` and `appointment_type`, so deserialization
 * failed and the screen showed nothing but its error state. `*_display` are
 * the Arabic labels the server already computes — prefer them over the raw
 * enum values.
 */
@Serializable
data class Appointment(
    val id: String,
    val patient: String = "",
    @SerialName("patient_name") val patientName: String? = null,
    val doctor: String = "",
    @SerialName("doctor_name") val doctorName: String? = null,
    /** ISO-8601 instant, e.g. 2026-09-05T09:30:00Z. */
    @SerialName("scheduled_at") val scheduledAt: String = "",
    @SerialName("duration_minutes") val durationMinutes: Int = 30,
    val status: String = "",
    @SerialName("status_display") val statusDisplay: String? = null,
    @SerialName("appointment_type") val appointmentType: String = "",
    @SerialName("type_display") val typeDisplay: String? = null,
    val priority: String = "NORMAL",
    val title: String = "",
    val location: String? = null,
    @SerialName("is_virtual") val isVirtual: Boolean = false,
    @SerialName("virtual_link") val virtualLink: String? = null,
    val notes: String? = null
)

/**
 * A telemedicine consultation — `GET telemedicine/consultations/`
 * (`ConsultationSerializer`).
 *
 * `telemedicine/sessions/` was a 404 and `session_url` does not exist; the
 * join link is `join_url`. [appointment] is nullable because a consultation
 * can be opened without one — as a non-null field it broke the whole list for
 * every ad-hoc consultation.
 *
 * The server also nests `messages`; the chat view is not built yet and unknown
 * keys are ignored, so it is deliberately left out.
 */
@Serializable
data class TelemedicineSession(
    val id: String,
    val patient: String = "",
    @SerialName("patient_name") val patientName: String? = null,
    val doctor: String = "",
    @SerialName("doctor_name") val doctorName: String? = null,
    val appointment: String? = null,
    @SerialName("scheduled_time") val scheduledTime: String? = null,
    val status: String = "",
    @SerialName("room_id") val roomId: String? = null,
    @SerialName("join_url") val joinUrl: String? = null,
    @SerialName("started_at") val startedAt: String? = null,
    @SerialName("ended_at") val endedAt: String? = null
)
