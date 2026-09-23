package com.securemed.app.hardware.scanner

import android.app.Activity
import android.content.Context
import android.net.Uri
import androidx.activity.result.IntentSenderRequest
import com.google.mlkit.vision.documentscanner.GmsDocumentScannerOptions
import com.google.mlkit.vision.documentscanner.GmsDocumentScanning
import com.google.mlkit.vision.documentscanner.GmsDocumentScanningResult
import kotlinx.coroutines.tasks.await
import java.io.File
import java.io.FileOutputStream

/**
 * Result data class representing a scanned medical document or lab report.
 */
data class ScannedDocument(
    val pdfUri: Uri?,
    val pageUris: List<Uri>,
    val pageCount: Int
)

/**
 * Helper to launch and process documents using Google Play Services Document Scanner.
 */
object DocumentScannerHelper {

    fun createScannerOptions(pageLimit: Int = 10): GmsDocumentScannerOptions {
        return GmsDocumentScannerOptions.Builder()
            .setGalleryImportAllowed(true)
            .setPageLimit(pageLimit)
            .setResultFormats(
                GmsDocumentScannerOptions.RESULT_FORMAT_JPEG,
                GmsDocumentScannerOptions.RESULT_FORMAT_PDF
            )
            .setScannerMode(GmsDocumentScannerOptions.SCANNER_MODE_FULL)
            .build()
    }

    suspend fun getStartScanIntentSender(activity: Activity, pageLimit: Int = 10): IntentSenderRequest {
        val options = createScannerOptions(pageLimit)
        val scanner = GmsDocumentScanning.getClient(options)
        val intentSender = scanner.getStartScanIntent(activity).await()
        return IntentSenderRequest.Builder(intentSender).build()
    }

    fun parseResult(resultCode: Int, data: android.content.Intent?): ScannedDocument? {
        if (resultCode != Activity.RESULT_OK || data == null) return null
        val scanningResult = GmsDocumentScanningResult.fromActivityResultIntent(data) ?: return null

        val pages = scanningResult.pages?.mapNotNull { it.imageUri } ?: emptyList()
        val pdfUri = scanningResult.pdf?.uri
        val pageCount = scanningResult.pdf?.pageCount ?: pages.size

        return ScannedDocument(
            pdfUri = pdfUri,
            pageUris = pages,
            pageCount = pageCount
        )
    }

    /**
     * Copies the scanned document (PDF or JPEG) into secure app-internal storage.
     */
    fun saveScannedFileSecurely(
        context: Context,
        sourceUri: Uri,
        fileName: String
    ): File? {
        return try {
            val destinationFile = File(context.filesDir, "scanned_docs/$fileName")
            destinationFile.parentFile?.mkdirs()

            context.contentResolver.openInputStream(sourceUri)?.use { input ->
                FileOutputStream(destinationFile).use { output ->
                    input.copyTo(output)
                }
            }
            destinationFile
        } catch (e: Exception) {
            android.util.Log.e("DocumentScannerHelper", "Error saving scanned file", e)
            null
        }
    }
}
