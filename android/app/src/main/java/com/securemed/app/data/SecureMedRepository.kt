package com.securemed.app.data

import android.content.Context
import com.securemed.app.data.api.ApiErrors
import com.securemed.app.data.api.SecureMedApi
import com.securemed.app.data.api.TwoFactorExpiredException
import com.securemed.app.data.local.LocalCache
import com.securemed.app.data.local.MedicationStore
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.data.model.*
import com.securemed.app.data.local.room.SecureMedDao
import com.securemed.app.data.local.room.PatientEntity
import com.securemed.app.data.local.room.MedicalRecordEntity
import com.securemed.app.reminders.ReminderScheduler
import com.securemed.app.security.BiometricHelper
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.serialization.KSerializer
import kotlinx.serialization.json.Json
import kotlinx.coroutines.tasks.await
import javax.inject.Inject
import javax.inject.Singleton
import androidx.work.WorkManager
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.NetworkType
import androidx.work.Constraints
import com.securemed.app.data.local.room.PendingSyncActionEntity
import com.securemed.app.data.sync.SyncWorker
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.UUID

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
    private val dao: SecureMedDao,
    @ApplicationContext private val context: Context
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

    // ===== SECURITY =====
    suspend fun checkDevice(
        fingerprint: String,
        macAddress: String?,
        email: String? = null
    ): Result<DeviceCheckResponse> = try {
        Result.success(api.checkDevice(DeviceCheckRequest(fingerprint, macAddress, email)))
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ===== AUTH =====
    /**
     * Password sign-in. May come back with a 2FA challenge instead of a
     * session — that response is returned as a success so the caller can act
     * on it; only a complete response opens a session here.
     */
    suspend fun login(email: String, password: String): Result<LoginResponse> = try {
        val response = api.login(LoginRequest(email, password))
        if (response.isAuthenticated) {
            storeSession(response)
            registerCurrentFcmToken() // best-effort; no-op without Firebase config
        }
        Result.success(response)
    } catch (e: Exception) {
        // Same translation as mfaLogin: a locked account, a throttled address and
        // a wrong password each have their own Arabic message from the server, and
        // all three reached the user as "HTTP 400 Bad Request" before this.
        Result.failure(Exception(ApiErrors.messageFor(e, "فشل تسجيل الدخول"), e))
    }

    /**
     * Completes a `requires_2fa` login with the code the user typed.
     *
     * Failures are translated here rather than in the UI: the server's own
     * Arabic message ("رمز التحقق غير صحيح") is the only thing that tells the
     * user which of the several ways this can fail actually happened, and
     * Retrofit would otherwise surface "HTTP 400 Bad Request".
     *
     * A 401 becomes [TwoFactorExpiredException] because it is the one failure
     * the user cannot retry from the code screen — the `mfa_token` is gone and
     * a new one only comes from `auth/login/`.
     */
    suspend fun mfaLogin(
        mfaToken: String,
        code: String,
        trustDevice: Boolean = false
    ): Result<LoginResponse> = try {
        val response = api.mfaLogin(MfaLoginRequest(mfaToken, code, trustDevice))
        // Same reasoning as biometricLogin: this endpoint has no second-factor
        // branch left to take, so a 200 without tokens is not a session.
        if (!response.isAuthenticated) error("تعذر إكمال التحقق بخطوتين")
        storeSession(response)
        registerCurrentFcmToken() // best-effort; no-op without Firebase config
        Result.success(response)
    } catch (e: Exception) {
        // messageFor reads the error body once, so it is called once and the
        // result reused. A wrong code carries the server's "رمز التحقق غير صحيح";
        // e.message alone would be Retrofit's "HTTP 400 Bad Request".
        val message = ApiErrors.messageFor(e, "تعذر التحقق من الرمز")
        Result.failure(
            if (ApiErrors.statusOf(e) == ApiErrors.UNAUTHORIZED) {
                TwoFactorExpiredException(message)
            } else {
                Exception(message, e)
            }
        )
    }

    /**
     * Step one of a biometric login: ask the server for something to sign.
     *
     * Split from [biometricLogin] because the biometric prompt has to run
     * between the two, and the prompt needs an Activity. Nothing here is secret:
     * an unknown account gets a decoy challenge that no signature can satisfy.
     */
    suspend fun getBiometricChallenge(email: String): Result<BiometricChallengeResponse> = try {
        Result.success(
            api.getBiometricChallenge(
                BiometricChallengeRequest(email, SecurePreferences.deviceId)
            )
        )
    } catch (e: Exception) {
        Result.failure(e)
    }

    /**
     * Step two: present the signature the unlocked Keystore key produced.
     *
     * The old single-call version asked for a challenge and then answered it with
     * `biometricResponse = "android-response-${challenge.challengeId}"` — the id
     * the server had just sent, echoed back. Anyone able to request a challenge
     * could produce that, with no key and no finger.
     */
    suspend fun biometricLogin(
        challengeId: String,
        signature: String
    ): Result<LoginResponse> = try {
        val response = api.biometricLogin(BiometricLoginRequest(challengeId, signature))
        // This endpoint has no second-factor branch: a 200 without tokens is
        // not a session, so it must not be reported as a successful login.
        if (!response.isAuthenticated) error("تعذر إكمال الدخول بالبصمة")
        storeSession(response)
        registerCurrentFcmToken() // best-effort; no-op without Firebase config
        Result.success(response)
    } catch (e: Exception) {
        Result.failure(e)
    }

    /** Writes the session. No-op for a response that carries none. */
    private fun storeSession(response: LoginResponse) {
        val tokens = response.tokens ?: return
        val user = response.user ?: return
        SecurePreferences.accessToken = tokens.access
        SecurePreferences.refreshToken = tokens.refresh
        SecurePreferences.userId = user.id
        SecurePreferences.userEmail = user.email
        SecurePreferences.userName = user.fullName
        SecurePreferences.userRole = user.role
    }

    /**
     * Register this device's public key against the signed-in account.
     *
     * The key pair is minted locally and only the public half is sent; the
     * private half stays in the Keystore, unusable until a fingerprint unlocks
     * it. If the request fails the local key is dropped again, so the device is
     * never left holding a private key the server has no counterpart for —
     * enrolling again simply mints a fresh pair.
     */
    suspend fun enrollBiometric(deviceName: String): Result<Unit> = try {
        val publicKey = BiometricHelper.createSigningKey()
            ?: error("تعذر إنشاء مفتاح البصمة على هذا الجهاز")
        api.enrollBiometric(
            BiometricEnrollRequest(
                deviceId = SecurePreferences.deviceId,
                deviceName = deviceName,
                platform = "ANDROID",
                publicKey = publicKey
            )
        )
        SecurePreferences.biometricEnabled = true
        Result.success(Unit)
    } catch (e: Exception) {
        BiometricHelper.deleteKey()
        Result.failure(e)
    }

    /**
     * Ends the session and wipes everything it left on the device.
     *
     * [allDevices] decides what the server is asked to do, and the difference is
     * carried by the *presence* of the `refresh` field: with a token the backend
     * ends only the session presenting it, and with the field absent it reads the
     * request as "end all of them" and denies every token the account holds
     * (`LogoutView`, `backend/apps/accounts/views.py:309-315`).
     *
     * That is also why a blank token is never sent. The call used to pass
     * `"refresh" to (refreshToken ?: "")`, and an empty string is falsy on the
     * server — so signing out on a phone whose refresh token had already been
     * dropped (a 401 that failed to refresh clears it) silently signed the user
     * out of every other device, including the workstation they were working on.
     */
    suspend fun logout(allDevices: Boolean = false) {
        // Patient data must not survive a session — wipe tokens, the offline
        // cache (medication plans + dose logs) and the Room PHI cache.
        val refresh = SecurePreferences.refreshToken
        val body: Map<String, String>? = when {
            allDevices -> emptyMap()
            !refresh.isNullOrBlank() -> mapOf("refresh" to refresh)
            // Nothing identifies this session to the server, and asking without a
            // token would end the account's other sessions too. The access token
            // expires on its own within 15 minutes.
            else -> null
        }
        if (body != null) {
            try {
                api.logout(body)
            } catch (_: Exception) {
                // Server-side invalidation is best-effort; local wipe always runs.
            }
        }

        // Order matters: alarms are keyed by plan id, so they have to be
        // dropped while the plans are still readable. Left armed, they keep
        // firing after sign-out and put the patient name and prescription on
        // the lock screen of a device with no session.
        try {
            ReminderScheduler(context).cancelAll()
        } catch (_: Exception) {
            // Never let alarm teardown block the credential wipe.
        }

        try {
            dao.clearAll()
        } catch (_: Exception) {
            // Same: a Room failure must not leave the tokens behind.
        }

        SecurePreferences.clearSession()
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
    suspend fun getPatients(): Result<List<Patient>> = getPatients(null)

    /**
     * Patients with an optional server-side search term. An empty result on
     * a *fresh* fetch is the server saying "no match"; on a network failure
     * the Room copy is searched locally instead so quick search keeps
     * working offline (by substring over the decrypted names the device
     * already holds).
     */
    suspend fun getPatients(search: String?): Result<List<Patient>> = try {
        val page = api.getPatients(search = search?.takeIf { it.isNotBlank() })
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
        // Offline, or the API is unreachable: fall back to the Room cache.
        // A search term filters the local copy the same way the server
        // would, so the user sees one consistent behaviour either way.
        val local = if (search.isNullOrBlank()) dao.getAllPatients()
        else dao.getAllPatients().filter {
            it.fullName.contains(search.trim(), ignoreCase = true) ||
                it.phone?.contains(search.trim(), ignoreCase = true) == true
        }
        if (local.isNotEmpty()) {
            val patients = local.map {
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

    suspend fun createPatient(request: PatientCreateRequest): Result<Patient> = try {
        val patient = api.createPatient(request)
        Result.success(patient)
    } catch (e: Exception) {
        val action = PendingSyncActionEntity(
            id = UUID.randomUUID().toString(),
            actionType = "CREATE_PATIENT",
            payloadJson = json.encodeToString(PatientCreateRequest.serializer(), request),
            createdAt = System.currentTimeMillis()
        )
        dao.insertPendingAction(action)
        scheduleSyncWorker()
        
        // Return a simulated success so the UI doesn't crash, 
        // using a temporary ID.
        Result.success(Patient(
            id = "temp_${action.id}",
            fullName = request.fullName,
            dateOfBirth = request.dateOfBirth,
            gender = request.gender,
            bloodType = request.bloodType,
            phone = request.phone,
            chronicConditions = request.chronicConditions
        ))
    }

    suspend fun createMedicalRecord(request: MedicalRecordCreateRequest): Result<MedicalRecord> = try {
        val record = api.createMedicalRecord(request)
        Result.success(record)
    } catch (e: Exception) {
        val action = PendingSyncActionEntity(
            id = UUID.randomUUID().toString(),
            actionType = "CREATE_MEDICAL_RECORD",
            payloadJson = json.encodeToString(MedicalRecordCreateRequest.serializer(), request),
            createdAt = System.currentTimeMillis()
        )
        dao.insertPendingAction(action)
        scheduleSyncWorker()

        // Return a simulated success.
        Result.success(MedicalRecord(
            id = "temp_${action.id}",
            title = request.title,
            content = request.content,
            recordType = request.recordType,
            recordTypeDisplay = request.recordType,
            createdByName = SecurePreferences.userName ?: "Unknown",
            isCritical = request.isCritical,
            createdAt = "Pending Sync"
        ))
    }

    /**
     * The patient-scoped profile aggregate: this is the call that makes a
     * patient page show *that patient's* records (ع6) — the server filters by
     * the patient's channels intersected with the caller's access, which the
     * global records list cannot express.
     */
    suspend fun getPatientProfile(patientId: String): Result<PatientProfileResponse> =
        cached("patient_profile_$patientId", PatientProfileResponse.serializer()) {
            api.getPatientProfile(patientId)
        }

    /** Upload a medical file into a channel (multipart, server caps at 20MB). */
    suspend fun uploadMedicalFile(
        fileBytes: ByteArray,
        fileName: String,
        mimeType: String,
        channelId: String,
        patientId: String?,
        title: String,
        description: String?,
        fileType: String
    ): Result<MedicalFileDto> = try {
        val mediaType = mimeType.toMediaTypeOrNull()
            ?: "application/octet-stream".toMediaTypeOrNull()!!
        val filePart = MultipartBody.Part.createFormData(
            "file", fileName, fileBytes.toRequestBody(mediaType)
        )
        fun text(value: String) = value.toRequestBody("text/plain".toMediaTypeOrNull())
        Result.success(
            api.uploadMedicalFile(
                file = filePart,
                channel = text(channelId),
                patient = patientId?.let(::text),
                title = text(title),
                description = description?.let(::text),
                fileType = text(fileType)
            )
        )
    } catch (e: Exception) {
        Result.failure(e)
    }

    private fun scheduleSyncWorker() {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()
        val request = OneTimeWorkRequestBuilder<SyncWorker>()
            .setConstraints(constraints)
            .build()
        WorkManager.getInstance(context).enqueue(request)
    }

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
                    createdByName = it.createdByName ?: "",
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
                        createdByName = it.createdByName.ifBlank { null },
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

    fun getPatientPagingSource(search: String? = null): com.securemed.app.data.paging.PatientPagingSource {
        return com.securemed.app.data.paging.PatientPagingSource(api, search)
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

    // ===== MEDICATION PLAN CLOUD SYNC =====

    /**
     * Push every device-local plan to the server (upsert by source_id).
     *
     * The plan id doubles as the server's source_id, so re-pushing the same
     * plan updates rather than duplicates. Best-effort: the device-local copy
     * is the source of truth for alarms; the cloud row is the durable twin
     * that survives a reinstall. Returns the number of plans synced.
     */
    suspend fun pushMedicationPlans(): Result<Int> = try {
        var pushed = 0
        MedicationStore.loadPlans().forEach { plan ->
            api.syncMedicationPlan(
                MedicationPlanUpsert(
                    patientId = plan.patientId,
                    name = plan.name,
                    dosage = plan.dosage,
                    times = plan.times,
                    startDate = plan.startDate,
                    endDate = plan.endDate,
                    instructions = plan.instructions,
                    sourceId = plan.id,
                    isActive = plan.isActive
                )
            )
            pushed++
        }
        Result.success(pushed)
    } catch (e: Exception) {
        Result.failure(e)
    }

    /**
     * Pull the server's plans for the accessible patients and merge them into
     * the local store: new server plans are added locally, existing ones are
     * updated (the server copy wins — it is the care team's regimen), and
     * local-only plans are kept for the next push. Returns the merged count.
     */
    suspend fun pullMedicationPlans(): Result<Int> = try {
        val remote = api.getMedicationPlans()
        val local = MedicationStore.loadPlans()
        val localById = local.associateBy { it.id }
        val merged = local.toMutableList()

        remote.forEach { dto ->
            val existing = localById[dto.sourceId]
            if (existing != null) {
                val idx = merged.indexOfFirst { it.id == existing.id }
                merged[idx] = existing.copy(
                    name = dto.name,
                    dosage = dto.dosage,
                    times = dto.times,
                    startDate = dto.startDate,
                    endDate = dto.endDate,
                    instructions = dto.instructions,
                    prescribedByName = dto.prescribedBy,
                    isActive = dto.isActive
                )
            } else {
                merged += Medication(
                    id = dto.sourceId ?: dto.id,
                    patientId = dto.patientId,
                    patientName = dto.patientName,
                    name = dto.name,
                    dosage = dto.dosage,
                    times = dto.times,
                    startDate = dto.startDate,
                    endDate = dto.endDate,
                    instructions = dto.instructions,
                    prescribedByName = dto.prescribedBy,
                    isActive = dto.isActive,
                    createdAt = dto.createdAt ?: java.time.LocalDateTime.now().toString()
                )
            }
        }
        MedicationStore.savePlans(merged)
        Result.success(merged.size)
    } catch (e: Exception) {
        Result.failure(e)
    }

    /**
     * Two-way sync: pull first so the local list reflects the care team's
     * updates, then push so the server holds every local plan. Returns a
     * short human summary for the UI.
     */
    suspend fun syncMedicationPlans(): Result<String> = try {
        val pulled = pullMedicationPlans().getOrDefault(-1)
        val pushed = pushMedicationPlans().getOrDefault(-1)
        Result.success(
            "تمت المزامنة — خطط محلية بعد الدمج: ${pulled.coerceAtLeast(0)}، مُرسلة: ${pushed.coerceAtLeast(0)}"
        )
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ===== CHANNEL MESSAGES (secure in-channel chat) =====

    suspend fun getChannelMessages(
        channelId: String,
        after: String? = null
    ): Result<List<ChannelMessage>> = try {
        Result.success(api.getChannelMessages(channelId, after))
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun sendChannelMessage(channelId: String, body: String): Result<ChannelMessage> = try {
        Result.success(api.sendChannelMessage(channelId, mapOf("body" to body)))
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ===== PUSH TOKEN REGISTRATION =====

    suspend fun registerPushToken(token: String, platform: String = "ANDROID"): Result<Unit> = try {
        api.registerPushToken(
            mapOf(
                "token" to token,
                "platform" to platform,
                "device_fingerprint" to (SecurePreferences.deviceId)
            )
        )
        Result.success(Unit)
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun unregisterPushToken(token: String): Result<Unit> = try {
        api.unregisterPushToken(mapOf("token" to token))
        Result.success(Unit)
    } catch (e: Exception) {
        Result.failure(e)
    }

    /**
     * Push the current FCM token to the server after a successful login, when
     * Firebase is actually provisioned. Missing google-services.json throws
     * IllegalStateException inside the SDK — that is the "push not configured"
     * case, swallowed deliberately; every other failure is reported.
     */
    suspend fun registerCurrentFcmToken(): Result<Unit> = try {
        val t = com.google.firebase.messaging.FirebaseMessaging.getInstance().token.await()
        registerPushToken(t)
    } catch (e: IllegalStateException) {
        // Firebase not provisioned — push is optional, skip silently.
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

    /** Book an appointment. The server rejects past times and doctor conflicts (400). */
    suspend fun createAppointment(request: AppointmentCreateRequest): Result<Appointment> = try {
        Result.success(api.createAppointment(request))
    } catch (e: Exception) {
        Result.failure(e)
    }

    /** Cancel an appointment — `POST appointments/{id}/cancel/`, optional reason. */
    suspend fun cancelAppointment(id: String, reason: String?): Result<Appointment> = try {
        val body = if (reason.isNullOrBlank()) emptyMap() else mapOf("reason" to reason)
        Result.success(api.cancelAppointment(id, body))
    } catch (e: Exception) {
        Result.failure(e)
    }

    /** Active doctors bookable by the caller (basin-scoped on the server). */
    suspend fun getDoctors(): Result<List<User>> =
        cachedPagedList("doctors", User.serializer()) { api.getUsersByRole("DOCTOR") }

    // ===== TELEMEDICINE =====
    suspend fun getTelemedicineSessions(): Result<List<TelemedicineSession>> =
        cachedPagedList("telemedicine_sessions", TelemedicineSession.serializer()) { api.getTelemedicineSessions() }
}
