package com.securemed.app.data.sync

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.securemed.app.data.api.SecureMedApi
import com.securemed.app.data.local.room.SecureMedDao
import com.securemed.app.data.model.MedicalRecordCreateRequest
import com.securemed.app.data.model.PatientCreateRequest
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.serialization.json.Json
import android.util.Log

@HiltWorker
class SyncWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted workerParams: WorkerParameters,
    private val dao: SecureMedDao,
    private val api: SecureMedApi
) : CoroutineWorker(appContext, workerParams) {

    private val json = Json { ignoreUnknownKeys = true }

    override suspend fun doWork(): Result {
        val pendingActions = dao.getPendingActions()
        
        if (pendingActions.isEmpty()) {
            return Result.success()
        }

        var hasFailures = false

        for (action in pendingActions) {
            try {
                when (action.actionType) {
                    "CREATE_PATIENT" -> {
                        val request = json.decodeFromString<PatientCreateRequest>(action.payloadJson)
                        api.createPatient(request)
                    }
                    "CREATE_MEDICAL_RECORD" -> {
                        val request = json.decodeFromString<MedicalRecordCreateRequest>(action.payloadJson)
                        api.createMedicalRecord(request)
                    }
                    else -> {
                        Log.w("SyncWorker", "Unknown action type: ${action.actionType}")
                    }
                }
                
                // If successful, remove from queue
                dao.deletePendingAction(action.id)
                
            } catch (e: Exception) {
                Log.e("SyncWorker", "Failed to sync action: ${action.id}", e)
                hasFailures = true
                // We keep it in the DB to retry later, unless it's a 4xx error which might never succeed.
                // For simplicity, we just keep it and let WorkManager retry the job.
            }
        }

        return if (hasFailures) Result.retry() else Result.success()
    }
}
