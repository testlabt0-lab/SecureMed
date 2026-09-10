package com.securemed.app.data.api

import com.securemed.app.data.model.*
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody
import kotlinx.serialization.json.JsonObject
import retrofit2.Response
import retrofit2.http.*

/**
 * Retrofit API interface for SecureMed backend.
 *
 * List endpoints return [PagedResponse] because the backend wraps every
 * collection in SecureMedPagination ({count, page, results…}).
 */
interface SecureMedApi {

    // ===== AUTH =====
    @POST("auth/login/")
    suspend fun login(@Body request: LoginRequest): LoginResponse

    /**
     * Second leg of a `requires_2fa` login. Returns the same [LoginResponse]
     * shape as `auth/login/`, but always with tokens — the server answers 400
     * for a wrong code and 401 once the 5-minute `mfa_token` has expired.
     */
    @POST("auth/2fa/login/")
    suspend fun mfaLogin(@Body request: MfaLoginRequest): LoginResponse

    @POST("auth/logout/")
    suspend fun logout(@Body body: Map<String, String>): Unit

    /** Delete this account (Play requirement) — the server verifies the password. */
    @DELETE("auth/account/")
    suspend fun deleteAccount(@Body body: Map<String, String>): Unit

    /**
     * Unused: the refresh that keeps a session alive runs through OkHttp's
     * Authenticator in [NetworkModule], which must not recurse back into this
     * client. Kept declared so the endpoint is visible here, and typed as
     * [RefreshResponse] rather than [TokenPair] so any future caller inherits the
     * rotation-dependent shape instead of the bug it caused.
     */
    @POST("auth/refresh/")
    suspend fun refreshToken(@Body body: Map<String, String>): RefreshResponse

    @GET("auth/users/me/")
    suspend fun getCurrentUser(): User

    @GET("auth/users/")
    suspend fun getUsers(@Query("page") page: Int = 1): PagedResponse<User>

    @POST("auth/users/{id}/activate/")
    suspend fun activateUser(@Path("id") id: String): Map<String, String>

    @POST("auth/users/{id}/deactivate/")
    suspend fun deactivateUser(@Path("id") id: String): Map<String, String>

    @POST("auth/biometric/enroll/")
    suspend fun enrollBiometric(@Body request: BiometricEnrollRequest): Unit

    @POST("auth/biometric/challenge/")
    suspend fun getBiometricChallenge(@Body request: BiometricChallengeRequest): BiometricChallengeResponse

    @POST("auth/biometric/login/")
    suspend fun biometricLogin(@Body request: BiometricLoginRequest): LoginResponse

    // ===== CHANNELS =====
    @GET("channels/")
    suspend fun getChannels(): PagedResponse<Channel>

    @GET("channels/{id}/")
    suspend fun getChannel(@Path("id") id: String): Channel

    @GET("channels/{id}/members/")
    suspend fun getChannelMembers(@Path("id") id: String): PagedResponse<ChannelMembership>

    /** In-channel secure chat (polling; ?after=<iso> for incremental fetch). */
    @GET("channels/{id}/messages/")
    suspend fun getChannelMessages(
        @Path("id") id: String,
        @Query("after") after: String? = null,
        @Query("limit") limit: Int = 200
    ): List<ChannelMessage>

    @POST("channels/{id}/messages/")
    suspend fun sendChannelMessage(
        @Path("id") id: String,
        @Body body: Map<String, String>
    ): ChannelMessage

    // ===== PATIENTS =====
    @GET("patients/")
    suspend fun getPatients(
        @Query("page") page: Int = 1,
        @Query("search") search: String? = null
    ): PagedResponse<Patient>

    @POST("patients/")
    suspend fun createPatient(
        @Body patient: PatientCreateRequest,
        /** Idempotency key for offline-queued creates; null on the direct path. */
        @retrofit2.http.Header("X-Client-Op-Id") clientOpId: String? = null
    ): Patient

    @GET("patients/{id}/")
    suspend fun getPatient(@Path("id") id: String): Patient

    @GET("patients/records/")
    suspend fun getMedicalRecords(
        @Query("channel") channelId: String? = null,
        @Query("page") page: Int = 1
    ): PagedResponse<MedicalRecord>

    @POST("patients/records/")
    suspend fun createMedicalRecord(
        @Body record: MedicalRecordCreateRequest,
        /** Idempotency key for offline-queued creates; null on the direct path. */
        @retrofit2.http.Header("X-Client-Op-Id") clientOpId: String? = null
    ): MedicalRecord

    /** Update a record — the server enforces the same channel-role rule as create. */
    @PATCH("patients/records/{id}/")
    suspend fun updateMedicalRecord(
        @Path("id") id: String,
        @Body record: MedicalRecordUpdateRequest
    ): MedicalRecord

    @DELETE("patients/records/{id}/")
    suspend fun deleteMedicalRecord(@Path("id") id: String): Unit

    /**
     * The patient-scoped aggregate (`PatientViewSet.profile`): the patient,
     * the records of *their* channels only (access-checked via
     * `get_viewable_channels`), their channels, files and counts. This is the
     * endpoint that makes a patient page show that patient's records — the
     * global `patients/records/` list cannot do that because `MedicalRecord`
     * carries no patient field.
     */
    @GET("patients/{id}/profile/")
    suspend fun getPatientProfile(@Path("id") id: String): PatientProfileResponse

    /**
     * Upload a medical file into a channel (`MedicalFileViewSet`, multipart).
     * The server validates the extension (jpg/jpeg/png/gif/pdf/dicom/dcm),
     * sniffs the signature and caps the size at 20MB.
     */
    @Multipart
    @POST("patients/files/")
    suspend fun uploadMedicalFile(
        @Part file: MultipartBody.Part,
        @Part("channel") channel: RequestBody,
        @Part("patient") patient: RequestBody?,
        @Part("title") title: RequestBody,
        @Part("description") description: RequestBody?,
        @Part("file_type") fileType: RequestBody
    ): MedicalFileDto

    // ===== SECURITY =====
    @POST("security/check-device/")
    suspend fun checkDevice(@Body request: DeviceCheckRequest): DeviceCheckResponse

    /** أجهزتي المسجلة (للمستخدم العادي). */
    @GET("security/my-devices/")
    suspend fun getMyDevices(): MyDevicesResponse

    /** "إزالة جهازي" — self-service deactivation (no blacklist entry). */
    @POST("security/devices/{id}/deactivate/")
    suspend fun deactivateMyDevice(@Path("id") id: String): Map<String, String>

    /** إزالة جهاز ببصمته مباشرة (الطريق المفضل للتطبيق). */
    @HTTP(method = "DELETE", path = "security/my-devices/", hasBody = true)
    suspend fun removeMyDevice(@Body request: RemoveDeviceRequest): Map<String, String>

    @GET("security/dashboard/")
    suspend fun getSecurityDashboard(): JsonObject

    // ===== NOTIFICATIONS =====
    @GET("notifications/")
    suspend fun getNotifications(@Query("page") page: Int = 1): PagedResponse<Notification>

    @GET("notifications/unread_count/")
    suspend fun getUnreadCount(): Map<String, Int>

    @POST("notifications/{id}/mark_read/")
    suspend fun markNotificationRead(@Path("id") id: String): Map<String, String>

    @POST("notifications/mark_all_read/")
    suspend fun markAllNotificationsRead(): Map<String, String>

    // ===== ANALYTICS =====
    @GET("analytics/dashboard/overview/")
    suspend fun getDashboardOverview(): DashboardStats

    // ===== PHARMACY =====
    @GET("pharmacy/prescriptions/")
    suspend fun getPrescriptions(@Query("page") page: Int = 1): PagedResponse<Prescription>

    /** Create a prescription (doctor = caller, items persist as `PrescriptionItem` rows). */
    @POST("pharmacy/prescriptions/")
    suspend fun createPrescription(@Body request: PrescriptionCreateRequest): Prescription

    @POST("pharmacy/prescriptions/{id}/dispense/")
    suspend fun dispensePrescription(@Path("id") id: String, @Body body: Map<String, String> = emptyMap()): Prescription

    /** Pharmacy catalog — the medication ids a prescription's items reference. */
    @GET("pharmacy/medications/")
    suspend fun getMedications(@Query("page") page: Int = 1): PagedResponse<InventoryMedication>

    /** Server twin of device-local medication plans (pull half of the sync). */
    @GET("pharmacy/medication-plans/")
    suspend fun getMedicationPlans(
        @Query("patient") patientId: String? = null,
        @Query("active") active: String? = null
    ): List<MedicationPlanDto>

    /** Push one plan (upsert by source_id). */
    @POST("pharmacy/medication-plans/")
    suspend fun syncMedicationPlan(@Body request: MedicationPlanUpsert): MedicationPlanDto

    // ===== PUSH =====
    @POST("notifications/push/register/")
    suspend fun registerPushToken(@Body body: Map<String, String>): Map<String, String>

    @DELETE("notifications/push/register/")
    suspend fun unregisterPushToken(@Body body: Map<String, String>): Map<String, String>

    // ===== LAB =====
    // Router basename is `orders` (apps/lab/urls.py); `lab/requests/` was a 404.
    @GET("lab/orders/")
    suspend fun getLabRequests(
        @Query("page") page: Int = 1,
        @Query("status") status: String? = null
    ): PagedResponse<LabTestRequest>

    @GET("lab/results/")
    suspend fun getLabResults(@Query("page") page: Int = 1): PagedResponse<LabResult>

    /** Enter a result — `performed_by` is the caller; abnormal/critical are server-computed. */
    @POST("lab/results/")
    suspend fun createLabResult(@Body result: LabResultCreateRequest): LabResult

    // ===== WARDS & BEDS =====
    @GET("wards/wards/")
    suspend fun getWards(@Query("page") page: Int = 1): PagedResponse<Ward>

    @GET("wards/beds/")
    suspend fun getBeds(
        @Query("page") page: Int = 1,
        @Query("status") status: String? = null
    ): PagedResponse<Bed>

    /** Admit a patient to a FREE bed — server rejects occupied beds and double admissions. */
    @POST("wards/assignments/")
    suspend fun assignBed(@Body request: BedAssignmentCreateRequest): BedAssignment

    @GET("wards/assignments/")
    suspend fun getActiveAssignments(
        @Query("page") page: Int = 1,
        @Query("active") active: String = "true"
    ): PagedResponse<BedAssignment>

    // ===== BILLING =====
    @GET("billing/invoices/")
    suspend fun getInvoices(
        @Query("page") page: Int = 1,
        @Query("status") status: String? = null
    ): PagedResponse<Invoice>

    /** Create an invoice — totals, VAT and insurance coverage are server-computed. */
    @POST("billing/invoices/")
    suspend fun createInvoice(@Body request: InvoiceCreateRequest): Invoice

    // ===== AUDIT (admin/auditor — server returns 403 otherwise) =====
    @GET("audit/logs/")
    suspend fun getAuditLogs(
        @Query("page") page: Int = 1,
        @Query("severity") severity: String? = null
    ): PagedResponse<AuditLogEntry>

    // ===== APPOINTMENTS =====
    @GET("appointments/")
    suspend fun getAppointments(@Query("page") page: Int = 1): PagedResponse<Appointment>

    /** Create an appointment (server runs it through `AppointmentCreateSerializer`). */
    @POST("appointments/")
    suspend fun createAppointment(@Body request: AppointmentCreateRequest): Appointment

    /** Cancel an appointment: `POST appointments/{id}/cancel/` with an optional reason. */
    @POST("appointments/{id}/cancel/")
    suspend fun cancelAppointment(
        @Path("id") id: String,
        @Body body: Map<String, String> = emptyMap()
    ): Appointment

    /** Doctors bookable by the current user (basin-scoped server-side). */
    @GET("auth/users/")
    suspend fun getUsersByRole(@Query("role") role: String): PagedResponse<User>

    // ===== TELEMEDICINE =====
    // Router basename is `consultations`; `telemedicine/sessions/` was a 404.
    @GET("telemedicine/consultations/")
    suspend fun getTelemedicineSessions(@Query("page") page: Int = 1): PagedResponse<TelemedicineSession>

    // ===== REPORTS =====
    /** Role-filtered catalog: the server never advertises a report the caller may not export. */
    @GET("reports/list/")
    suspend fun getReportCatalog(): ReportCatalogResponse

    /** Download a report as PDF/Excel bytes (the server audits every export). */
    @Streaming
    @GET("reports/{report_id}/")
    suspend fun downloadReport(
        @Path("report_id") reportId: String,
        @Query("format") format: String = "pdf",
        @Query("start_date") startDate: String? = null,
        @Query("end_date") endDate: String? = null
    ): Response<ResponseBody>
}
