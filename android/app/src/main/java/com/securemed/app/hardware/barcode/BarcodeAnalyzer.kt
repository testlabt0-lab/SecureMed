package com.securemed.app.hardware.barcode

import androidx.annotation.OptIn
import androidx.camera.core.ExperimentalGetImage
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage

/**
 * Ultra-fast ML Kit Barcode Analyzer for CameraX.
 * Processes single frames using STRATEGY_KEEP_ONLY_LATEST to avoid latency.
 */
class BarcodeAnalyzer(
    private val onBarcodeDetected: (String) -> Unit
) : ImageAnalysis.Analyzer {

    private val options = BarcodeScannerOptions.Builder()
        .setBarcodeFormats(
            Barcode.FORMAT_QR_CODE,
            Barcode.FORMAT_CODE_128,
            Barcode.FORMAT_CODE_39,
            Barcode.FORMAT_EAN_13,
            Barcode.FORMAT_EAN_8,
            Barcode.FORMAT_DATA_MATRIX,
            Barcode.FORMAT_PDF417
        )
        .build()

    private val scanner = BarcodeScanning.getClient(options)

    @Volatile
    private var isScanningEnabled = true

    @OptIn(ExperimentalGetImage::class)
    override fun analyze(imageProxy: ImageProxy) {
        val mediaImage = imageProxy.image
        if (mediaImage != null && isScanningEnabled) {
            val inputImage = InputImage.fromMediaImage(
                mediaImage,
                imageProxy.imageInfo.rotationDegrees
            )
            scanner.process(inputImage)
                .addOnSuccessListener { barcodes ->
                    val firstBarcode = barcodes.firstOrNull()?.rawValue
                    if (!firstBarcode.isNullOrBlank() && isScanningEnabled) {
                        isScanningEnabled = false
                        onBarcodeDetected(firstBarcode)
                    }
                }
                .addOnFailureListener {
                    // Fail gracefully on obscure or unparseable frames
                }
                .addOnCompleteListener {
                    imageProxy.close()
                }
        } else {
            imageProxy.close()
        }
    }

    fun resume() {
        isScanningEnabled = true
    }

    fun pause() {
        isScanningEnabled = false
    }
}
