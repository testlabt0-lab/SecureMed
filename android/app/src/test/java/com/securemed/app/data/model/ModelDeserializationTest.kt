package com.securemed.app.data.model

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Model deserialization against REAL server response shapes (4-1).
 *
 * م10 documented how two fields broke whole lists; these tests decode actual
 * JSON the backend emits (field names from the serializers, not from what the
 * client wishes they were) so a renamed column degrades one default value —
 * never a screen.
 */
class ModelDeserializationTest {

    private val json = Json { ignoreUnknownKeys = true; coerceInputValues = true }

    @Test
    fun `MedicalRecord decodes a null created_by_name and unknown fields`() {
        // `created_by` is nullable on the server (deleted/system actor), and
        // real responses carry extra envelope fields the model ignores.
        val body = """
        {
            "id": "9f1c-…",
            "title": "ملاحظات الكشف",
            "content": "الضغط مرتفع، أوصيت بمضاد حيوي",
            "record_type": "NOTES",
            "record_type_display": "ملاحظات",
            "created_by_name": null,
            "is_critical": false,
            "created_at": "2026-09-09T10:30:00Z",
            "channel": "some-channel-uuid",
            "unknown_future_field": 42
        }
        """.trimIndent()

        val record = json.decodeFromString(MedicalRecord.serializer(), body)

        assertEquals("ملاحظات الكشف", record.title)
        assertNull(record.createdByName)
        assertEquals("ملاحظات", record.recordTypeDisplay)
    }

    @Test
    fun `Notification decodes a numeric data payload`() {
        // `data` is a free JSONField on the server — a number used to sink
        // the whole notification list.
        val body = """
        {
            "id": "n-1",
            "notification_type": "LAB_RESULT",
            "priority": "HIGH",
            "title": "نتيجة تحليل جاهزة",
            "message": "نتيجة التحليل جاهزة للمراجعة",
            "is_read": false,
            "created_at": "2026-09-09T09:00:00Z",
            "data": 7
        }
        """.trimIndent()

        val notification = json.decodeFromString(Notification.serializer(), body)

        assertEquals("نتيجة تحليل جاهزة", notification.title)
        assertEquals("HIGH", notification.priority)
        assertTrue(!notification.isRead)
    }

    @Test
    fun `Appointment decodes the real server field names`() {
        // The server sends scheduled_at/appointment_type — the earlier shape
        // asked for appointment_date/consultation_type and decoded nothing.
        val body = """
        {
            "id": "a-1",
            "patient_name": "المريض أحمد",
            "doctor_name": "الدكتور سالم",
            "scheduled_at": "2026-09-15T14:30:00Z",
            "appointment_type": "FOLLOW_UP",
            "appointment_type_display": "متابعة",
            "status": "SCHEDULED",
            "status_display": "مجدول",
            "priority": "MEDIUM",
            "title": "مراجعة شهرية"
        }
        """.trimIndent()

        val appointment = json.decodeFromString(Appointment.serializer(), body)

        assertEquals("2026-09-15T14:30:00Z", appointment.scheduledAt)
        assertEquals("FOLLOW_UP", appointment.appointmentType)
        assertEquals("المريض أحمد", appointment.patientName)
    }

    @Test
    fun `RefreshResponse tolerates a missing refresh token`() {
        // A refresh response that carries only `access` must not fail to
        // decode — failing here meant the caller treated a valid session as
        // unrecoverable and cleared it.
        val body = """{"access": "new-access-token"}"""

        val tokens = json.decodeFromString(RefreshResponse.serializer(), body)

        assertEquals("new-access-token", tokens.access)
        assertNull(tokens.refresh)
    }

    @Test
    fun `LabTestRequest decodes a full order envelope`() {
        val body = """
        {
            "id": "lab-1",
            "patient": "p-uuid",
            "patient_name": "المريضة سارة",
            "test_name": "صورة دم كاملة",
            "test_category": "HEMATOLOGY",
            "doctor_name": "الدكتور سالم",
            "status": "PENDING",
            "priority": "HIGH",
            "clinical_notes": "صيام مطلوب",
            "created_at": "2026-09-09T08:00:00Z"
        }
        """.trimIndent()

        val order = json.decodeFromString(LabTestRequest.serializer(), body)

        assertEquals("صورة دم كاملة", order.testName)
        assertEquals("المريضة سارة", order.patientName)
        assertEquals("HIGH", order.priority)
    }
}
