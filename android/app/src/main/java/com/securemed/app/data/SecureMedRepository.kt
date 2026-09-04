package com.securemed.app.data

import com.securemed.app.data.api.SecureMedApi
import com.securemed.app.data.local.LocalCache
import com.securemed.app.data.local.MedicationStore
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.data.model.*
import com.securemed.app.data.local.room.SecureMedDao
import com.securemed.app.data.local.room.PatientEntity
import com.securemed.app.data.local.room.MedicalRecordEntity
import kotlinx.serialization.KSerializer
import kotlinx.serialization.json.Json
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Repository for authentication and data operations.
 *
 * GET responses are mirrored into Room or [LocalCache]; when a request fails
 * (offline / server unreachable) the last cached copy is served so the
 * app stays browsable. Medication plans live entirely on the device via
 * [MedicationStore] — dose reminders must work without connectivity.
 *
 * The [api] and [dao] dependencies are provided by Hilt, making this class testable.
 */
@Singleton
class SecureMedRepository @Inject constructor(
    private val api: SecureMedApi,
    private val dao: SecureMedDao
) {

    private val json = Json { ignoreUnknownKeys = true; coerceInputValues = true }

    /** Fetch-through cache: network first, fall back to the last cached copy. */
    private inline fun <T> cached(
        key: String,
        serializer: KSerializer<T>,
        fetch: () -> T
    ): Result<T> = try {
        val data = fetch()
        try {
            LocalCache.save(key, json.encodeToString(serializer, data))
        } catch (_: Exception) {
            // Cache write failures must never fail a successful request.
        }
        Result.success(data)
    } catch (e: Exception) {
        val cachedJson = LocalCache.load(key)
        if (cachedJson != null) {
            try {
                Result.success(json.decodeFromString(serializer, cachedJson))
            } catch (_: Exception) {
                Result.failure(e)
            }
        } else {
            Result.failure(e)
        }
    }

    /** Paged list endpoint cached by envelope, exposed as a plain list. */
    private inline fun <T> cachedPagedList(
        key: String,
        serializer: KSerializer<T>,
        fetch: () -> PagedResponse<T>
    ): Result<List<T>> = try {
        val page = fetch()
        try {
            LocalCache.save(key, json.encodeToString(PagedResponse.serializer(serializer), page))
        } catch (_: Exception) {
        }
        Result.success(page.results)
    } catch (e: Exception) {
        val cachedJson = LocalCache.load(key)
        if (cachedJson != null) {
            try {
                Result.success(json.decodeFromString(PagedResponse.serializer(serializer), cachedJson).results)
            } catch (_: Exception) {
                Result.failure(e)
            }
        } else {
            Result.failure(e)
        }
    }

    // ===== AUTH =====
    suspend fun login(email: String, password: String): Result<LoginResponse> = try {
        val response = api.login(LoginRequest(email, password))
        storeSession(response)
        Result.success(response)
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun biometricLogin(
        email: String,
        biometricTemplate: String
    ): Result<LoginResponse> = try {
        val challenge = api.getBiometricChallenge(
            BiometricChallengeRequest(email, SecurePreferences.deviceId)
        )
        val response = api.biometricLogin(
            BiometricLoginRequest(
                challengeId = challenge.challengeId,
                biometricResponse = "android-response-${challenge.challengeId}",
                biometricTemplate = biometricTemplate
            )
        )
        storeSession(response)
        Result.success(response)
    } catch (e: Exception) {
        Result.failure(e)
    }

    private fun storeSession(response: LoginResponse) {
        SecurePreferences.accessToken = response.tokens.access
        SecurePreferences.refreshToken = response.tokens.refresh
        SecurePreferences.userId = response.user.id
        SecurePreferences.userEmail = response.user.email
        SecurePreferences.userName = response.user.fullName
        SecurePreferences.userRole = response.user.role
    }

    suspend fun enrollBiometric(deviceName: String, biometricTemplate: String): Result<Unit> = try {
        api.enrollBiometric(
            BiometricEnrollRequest(
                deviceId = SecurePreferences.deviceId,
                deviceName = deviceName,
                platform = "ANDROID",
                biometricTemplate = biometricTemplate
            )
        )
        SecurePreferences.biometricEnabled = true
        Result.success(Unit)
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun logout() {
        // Patient data must not survive a session — wipe tokens and the
        // offline cache (medication plans + dose logs included).
        try {
            api.logout(mapOf("refresh" to (SecurePreferences.refreshToken ?: "")))
        } catch (_: Exception) {
            // Server-side invalidation is best-effort; local wipe always runs.
        }
        SecurePreferences.clear()
        LocalCache.clear()
    }

    // ===== USERS (admin) =====
    suspend fun getUsers(): Result<List<User>> =
        cachedPagedList("users", User.serializer()) { api.getUsers() }

    suspend fun activateUser(id: String): Result<String> = try {
        val response = api.activateUser(id)
        Result.success(response["detail"] ?: "تم تفعيل الحساب")
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun deactivateUser(id: String): Result<String> = try {
        val response = api.deactivateUser(id)
        Result.success(response["detail"] ?: "تم إيقاف الحساب")
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ===== CHANNELS =====
    suspend fun getChannels(): Result<List<Channel>> =
        cachedPagedList("channels", Channel.serializer()) { api.getChannels() }

    suspend fun getChannel(id: String): Result<Channel> =
        cached("channel_$id", Channel.serializer()) { api.getChannel(id) }

    suspend fun getChannelMembers(id: String): Result<List<ChannelMembership>> =
        cachedPagedList("channel_${id}_members", ChannelMembership.serializer()) { api.getChannelMembers(id) }

    // ===== PATIENTS =====
    suspend fun getPatients(): Result<List<Patient>> = try {
        val page = api.getPatients()
        val patients = page.results
        val entities = patients.map {
            PatientEntity(
                id = it.id,
                fullName = it.fullName,
                dateOfBirth = it.dateOfBirth,
                gender = it.gender,
                bloodType = it.bloodType,
                age = it.age,
                phone = it.phone,
                chronicConditions = it.chronicConditions
            )
        }
        dao.insertPatients(entities)
        Result.success(patients)
    } catch (e: Exception) {
        val entities = dao.getAllPatients()
        if (entities.isNotEmpty()) {
            val patients = entities.map {
                Patient(
                    id = it.id,
                    fullName = it.fullName,
                    dateOfBirth = it.dateOfBirth,
                    gender = it.gender,
                    bloodType = it.bloodType,
                    age = it.age,
                    phone = it.phone,
                    chronicConditions = it.chronicConditions
                )
            }
            Result.success(patients)
        } else {
            Result.failure(e)
        }
    }

    suspend fun getPatient(id: String): Result<Patient> =
        cached("patient_$id", Patient.serializer()) { api.getPatient(id) }

    suspend fun getMedicalRecords(channelId: String? = null): Result<List<MedicalRecord>> {
        if (channelId == null) {
            return cachedPagedList("records", MedicalRecord.serializer()) { api.getMedicalRecords(channelId) }
        }
        return try {
            val page = api.getMedicalRecords(channelId)
            val records = page.results
            val entities = records.map {
                MedicalRecordEntity(
                    id = it.id,
                    channelId = channelId,
                    title = it.title,
                    content = it.content,
                    recordType = it.recordType,
                    recordTypeDisplay = it.recordTypeDisplay,
                    createdByName = it.createdByName,
                    isCritical = it.isCritical,
                    createdAt = it.createdAt
                )
            }
            dao.insertRecords(entities)
            Result.success(records)
        } catch (e: Exception) {
            val entities = dao.getRecordsByChannel(channelId)
            if (entities.isNotEmpty()) {
                val records = entities.map {
                    MedicalRecord(
                        id = it.id,
                        title = it.title,
                        content = it.content,
                        recordType = it.recordType,
                        recordTypeDisplay = it.recordTypeDisplay,
                        createdByName = it.createdByName,
                        isCritical = it.isCritical,
                        createdAt = it.createdAt
                    )
                }
                Result.success(records)
            } else {
                Result.failure(e)
            }
        }
    }

    fun getPatientPagingSource(): com.securemed.app.data.paging.PatientPagingSource {
        return com.securemed.app.data.paging.PatientPagingSource(api)
    }

    // ===== SECURITY =====
    suspend fun getSecurityDashboard(): Result<Map<String, String>> = try {
        val obj = api.getSecurityDashboard()
        Result.success(obj.mapValues { (_, v) -> v.toString() })
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ===== NOTIFICATIONS =====
    suspend fun getNotifications(): Result<List<Notification>> =
        cachedPagedList("notifications", Notification.serializer()) { api.getNotifications() }

    suspend fun getUnreadCount(): Result<Map<String, Int>> = try {
        Result.success(api.getUnreadCount())
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun markNotificationRead(id: String): Result<Unit> = try {
        api.markNotificationRead(id)
        Result.success(Unit)
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun markAllNotificationsRead(): Result<Unit> = try {
        api.markAllNotificationsRead()
        Result.success(Unit)
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ===== ANALYTICS =====
    suspend fun getDashboardOverview(): Result<DashboardStats> = try {
        Result.success(api.getDashboardOverview())
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ===== MEDICATION PLANS (device-local, offline-first) =====

    fun getMedications(): Result<List<Medication>> =
        Result.success(MedicationStore.loadPlans())

    fun getTodayDoses(): Result<TodayDosesResponse> =
        Result.success(MedicationStore.todayDosesResponse())

    fun getAdherence(): Result<AdherenceStats> =
        Result.success(MedicationStore.adherenceStats())

    fun createMedication(
        patientId: String,
        patientName: String,
        name: String,
        dosage: String,
        doseTimes: List<String>,
        instructions: String
    ): Result<Medication> = try {
        val plan = Medication(
            id = java.util.UUID.randomUUID().toString(),
            patientId = patientId,
            patientName = patientName,
            name = name,
            dosage = dosage,
            times = doseTimes,
            startDate = java.time.LocalDate.now().toString(),
            instructions = instructions,
            prescribedByName = SecurePreferences.userName ?: "",
            isActive = true,
            createdAt = java.time.LocalDateTime.now().toString()
        )
        MedicationStore.addPlan(plan)
        Result.success(plan)
    } catch (e: Exception) {
        Result.failure(e)
    }

    fun logDose(medicationId: String, scheduledFor: String, status: String): Result<Unit> = try {
        MedicationStore.logDose(medicationId, scheduledFor, status)
        Result.success(Unit)
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ===== PHARMACY =====
    suspend fun getPrescriptions(): Result<List<Prescription>> =
        cachedPagedList("prescriptions", Prescription.serializer()) { api.getPrescriptions() }

    suspend fun dispensePrescription(id: String): Result<Prescription> = try {
        val result = api.dispensePrescription(id)
        Result.success(result)
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ===== LAB =====
    suspend fun getLabRequests(): Result<List<LabTestRequest>> =
        cachedPagedList("lab_requests", LabTestRequest.serializer()) { api.getLabRequests() }

    // ===== APPOINTMENTS =====
    suspend fun getAppointments(): Result<List<Appointment>> =
        cachedPagedList("appointments", Appointment.serializer()) { api.getAppointments() }

    // ===== TELEMEDICINE =====
    suspend fun getTelemedicineSessions(): Result<List<TelemedicineSession>> =
        cachedPagedList("telemedicine_sessions", TelemedicineSession.serializer()) { api.getTelemedicineSessions() }
}
