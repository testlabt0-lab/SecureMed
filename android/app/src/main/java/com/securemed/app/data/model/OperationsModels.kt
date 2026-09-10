package com.securemed.app.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * A lab result — `GET lab/results/` (`LabResultSerializer`), plus the
 * parent-order test fields the screen needs (`LabOrderSerializer` nests the
 * result, but the results list is what a clinician scans first).
 *
 * The result row alone does not name its test; the lab app keeps it simple by
 * carrying only the order id and letting the (paged) orders list supply the
 * test names. Critical/abnormal flags are computed server-side.
 */
@Serializable
data class LabResult(
    val id: String,
    val order: String,
    @SerialName("numeric_value") val numericValue: Double? = null,
    @SerialName("text_value") val textValue: String? = null,
    @SerialName("is_abnormal") val isAbnormal: Boolean = false,
    @SerialName("is_critical") val isCritical: Boolean = false,
    val notes: String? = null,
    @SerialName("performed_by_name") val performedByName: String? = null,
    @SerialName("validated_by_name") val validatedByName: String? = null,
    @SerialName("validated_at") val validatedAt: String? = null,
    @SerialName("created_at") val createdAt: String = ""
)

/** A ward with its room/bed counts (`WardSerializer`). */
@Serializable
data class Ward(
    val id: String,
    val name: String,
    val floor: String? = null,
    val description: String? = null,
    @SerialName("is_active") val isActive: Boolean = true,
    @SerialName("total_beds") val totalBeds: Int = 0,
    @SerialName("occupied_beds") val occupiedBeds: Int = 0
)

/** A bed (`BedSerializer`) — statuses come from the server's own choices. */
@Serializable
data class Bed(
    val id: String,
    @SerialName("bed_number") val bedNumber: String = "",
    @SerialName("room_number") val roomNumber: String = "",
    @SerialName("room_type") val roomType: String? = null,
    @SerialName("ward_name") val wardName: String = "",
    val status: String = "FREE",
    val notes: String? = null
)

/** An invoice (`InvoiceSerializer`). */
@Serializable
data class Invoice(
    val id: String,
    val patient: String = "",
    @SerialName("patient_name") val patientName: String? = null,
    @SerialName("total_amount") val totalAmount: Double = 0.0,
    val discount: Double = 0.0,
    @SerialName("insurance_covered") val insuranceCovered: Double = 0.0,
    @SerialName("patient_payable") val patientPayable: Double = 0.0,
    @SerialName("final_total_with_vat") val finalTotalWithVat: Double = 0.0,
    val status: String = "DRAFT",
    @SerialName("due_date") val dueDate: String? = null,
    @SerialName("created_at") val createdAt: String = ""
)

/** An audit log row (`AuditLogSerializer`) — admin/auditor eyes only. */
@Serializable
data class AuditLogEntry(
    val id: String,
    @SerialName("user_name") val userName: String? = null,
    @SerialName("user_email") val userEmail: String? = null,
    @SerialName("event_type") val eventType: String = "",
    @SerialName("event_type_display") val eventTypeDisplay: String = "",
    val severity: String = "INFO",
    @SerialName("severity_display") val severityDisplay: String? = null,
    @SerialName("ip_address") val ipAddress: String? = null,
    val path: String? = null,
    val method: String? = null,
    @SerialName("device_fingerprint") val deviceFingerprint: String? = null,
    @SerialName("risk_score") val riskScore: Int = 0,
    val timestamp: String = ""
)

/** Body of `POST lab/results/` (`LabResultCreateSerializer`). */
@Serializable
data class LabResultCreateRequest(
    val order: String,
    @SerialName("numeric_value") val numericValue: Double? = null,
    @SerialName("text_value") val textValue: String? = null,
    val notes: String? = null
)

/** Body of `POST wards/assignments/` (`BedAssignmentCreateSerializer`). */
@Serializable
data class BedAssignmentCreateRequest(
    val bed: String,
    val patient: String,
    @SerialName("diagnosis_on_admission") val diagnosisOnAdmission: String? = null
)

/** An active admission (`BedAssignmentSerializer` read shape). */
@Serializable
data class BedAssignment(
    val id: String,
    val bed: String,
    @SerialName("bed_details") val bedDetails: Bed? = null,
    val patient: String = "",
    @SerialName("patient_name") val patientName: String? = null,
    @SerialName("admitted_by_name") val admittedByName: String? = null,
    @SerialName("diagnosis_on_admission") val diagnosisOnAdmission: String? = null,
    @SerialName("is_active") val isActive: Boolean = true,
    @SerialName("admission_date") val admissionDate: String? = null
)

/** Body of `POST billing/invoices/` (`InvoiceCreateSerializer`). */
@Serializable
data class InvoiceCreateRequest(
    val patient: String,
    val discount: Double = 0.0,
    @SerialName("due_date") val dueDate: String? = null,
    val items: List<InvoiceItemRequest>
)

/** One invoice line — `total_price` is computed server-side (quantity × unit). */
@Serializable
data class InvoiceItemRequest(
    val description: String,
    val quantity: Int,
    @SerialName("unit_price") val unitPrice: Double
)

/** A row of `GET reports/list/` — already role-filtered server-side. */
@Serializable
data class ReportCatalogItem(
    val id: String,
    val title: String,
    val description: String = "",
    val formats: List<String> = listOf("pdf")
)

@Serializable
data class ReportCatalogResponse(
    val results: List<ReportCatalogItem> = emptyList()
)
