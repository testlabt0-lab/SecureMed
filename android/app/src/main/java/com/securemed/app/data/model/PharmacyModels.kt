package com.securemed.app.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class InventoryMedication(
    val id: String,
    val name: String,
    @SerialName("scientific_name") val scientificName: String? = null,
    val barcode: String? = null,
    @SerialName("stock_quantity") val stockQuantity: Int = 0,
    @SerialName("unit_price") val unitPrice: Double = 0.0,
    @SerialName("is_active") val isActive: Boolean = true
)

@Serializable
data class PrescriptionItem(
    val id: Int = 0,
    val medication: String,
    @SerialName("medication_name") val medicationName: String? = null,
    val dosage: String,
    val frequency: String,
    @SerialName("duration_days") val durationDays: Int,
    val quantity: Int
)

@Serializable
data class Prescription(
    val id: String,
    val patient: String,
    @SerialName("patient_name") val patientName: String? = null,
    val doctor: String,
    @SerialName("doctor_name") val doctorName: String? = null,
    @SerialName("diagnosis_code") val diagnosisCode: String? = null,
    val status: String,
    val items: List<PrescriptionItem> = emptyList(),
    @SerialName("created_at") val createdAt: String
)
