package com.securemed.app.data.sync

import android.content.Context
import android.util.Log
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.securemed.app.data.api.ApiErrors
import com.securemed.app.data.api.SecureMedApi
import com.securemed.app.data.local.room.SecureMedDao
import com.securemed.app.data.model.MedicalRecordCreateRequest
import com.securemed.app.data.model.PatientCreateRequest
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.serialization.json.Json
import retrofit2.HttpException
import java.io.IOException

/**
 * UI-visible outcome of the last sync pass.
 *
 * The queue lives in a database the UI does not watch, so a poison action
 * that had to be dropped used to vanish silently. Workers post here; view
 * models that care (patient detail, patients list) collect and surface it.
 */
object SyncEvents {
    private val _message = MutableStateFlow<String?>(null)
    val message: StateFlow<String?> = _message

    fun post(message: String?) {
        _message.value = message
    }
}

/**
 * Raised for a create that was queued offline instead of reaching the
 * server. Distinct type so the UI can tell "held locally, will sync" apart
 * from a hard failure — the old queue faked a success with a `temp_` id,
 * which read as a saved record until it silently wasn't one.
 */
class SyncQueuedException(message: String) : IOException(message)

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
                        api.createPatient(request, action.clientOpId)
                    }
                    "CREATE_MEDICAL_RECORD" -> {
                        val request = json.decodeFromString<MedicalRecordCreateRequest>(action.payloadJson)
                        api.createMedicalRecord(request, action.clientOpId)
                    }
                    else -> {
                        Log.w(TAG, "Unknown action type: ${action.actionType}")
                    }
                }

                // If successful, remove from queue
                dao.deletePendingAction(action.id)

            } catch (e: Exception) {
                val status = (e as? HttpException)?.code()
                if (status != null && status in 400..499) {
                    // The server understood and rejected this one — a 4xx
                    // re-sent forever is not a retry, it is a denial-of-self
                    // that pins a poison row (and its traffic budget) in the
                    // queue for the life of the install. Drop it and say so.
                    Log.e(TAG, "Dropping permanently-rejected action: ${action.id}", e)
                    dao.deletePendingAction(action.id)
                    SyncEvents.post(
                        "رُفضت عملية ${action.actionType.removePrefix("CREATE_").lowercase()} " +
                            "من الخادم ولن تُعاد المحاولة: ${ApiErrors.messageFor(e, "سبب أمني أو تحقق")}"
                    )
                } else {
                    Log.e(TAG, "Failed to sync action: ${action.id}", e)
                    hasFailures = true
                    dao.setPendingActionFailureReason(
                        action.id, ApiErrors.messageFor(e, "تعذر الوصول للخادم")
                    )
                }
            }
        }

        if (hasFailures) SyncEvents.post("بعض العمليات المحلية بانتظار المزامنة — سيُعاد الإرسال تلقائياً")

        return if (hasFailures) Result.retry() else Result.success()
    }

    private companion object {
        const val TAG = "SyncWorker"
    }
}
