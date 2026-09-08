package com.securemed.app.data.api

import com.securemed.app.data.model.*
import okhttp3.MultipartBody
import okhttp3.RequestBody
import kotlinx.serialization.json.JsonObject
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
    suspend fun getUsers(): PagedResponse<User>

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
    suspend fun createPatient(@Body patient: PatientCreateRequest): Patient

    @GET("patients/{id}/")
    suspend fun getPatient(@Path("id") id: String): Patient

    @GET("patients/records/")
    suspend fun getMedicalRecords(@Query("channel") channelId: String? = null): PagedResponse<MedicalRecord>

    @POST("patients/records/")
    suspend fun createMedicalRecord(@Body record: MedicalRecordCreateRequest): MedicalRecord

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

    @GET("security/dashboard/")
    suspend fun getSecurityDashboard(): JsonObject

    // ===== NOTIFICATIONS =====
    @GET("notifications/")
    suspend fun getNotifications(): PagedResponse<Notification>

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

    @POST("pharmacy/prescriptions/{id}/dispense/")
    suspend fun dispensePrescription(@Path("id") id: String, @Body body: Map<String, String> = emptyMap()): Prescription

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
    suspend fun getLabRequests(@Query("page") page: Int = 1): PagedResponse<LabTestRequest>

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
}
