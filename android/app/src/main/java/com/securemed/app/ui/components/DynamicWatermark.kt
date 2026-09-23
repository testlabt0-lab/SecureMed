package com.securemed.app.ui.components

import android.graphics.Paint
import android.graphics.Typeface
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import com.securemed.app.data.local.SecurePreferences
import kotlinx.coroutines.delay
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Dynamic PHI Watermark for sensitive healthcare screens.
 *
 * Renders a repeating, semi-transparent, rotated grid displaying
 * the authenticated user's name, user ID prefix, and live timestamp.
 *
 * This provides immediate forensic attribution if an authorized user attempts
 * to photograph the device screen with an external camera, bypassing FLAG_SECURE.
 *
 * Touches pass through completely to underlying content.
 */
@Composable
fun DynamicWatermark(
    modifier: Modifier = Modifier,
    enabled: Boolean = SecurePreferences.isWatermarkEnabled,
    customUser: String? = null,
    content: @Composable () -> Unit
) {
    Box(modifier = modifier) {
        content()
        if (enabled) {
            DynamicWatermarkOverlay(customUser = customUser)
        }
    }
}

@Composable
fun DynamicWatermarkOverlay(
    modifier: Modifier = Modifier,
    customUser: String? = null,
    alpha: Float = 0.08f
) {
    if (!SecurePreferences.isWatermarkEnabled) return

    val userName = customUser
        ?: SecurePreferences.userName?.ifBlank { null }
        ?: "SecureMed User"
    val userId = SecurePreferences.userId?.take(8) ?: ""

    // Live clock updated every 30 seconds
    var timestamp by remember {
        mutableStateOf(SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault()).format(Date()))
    }

    LaunchedEffect(Unit) {
        while (true) {
            delay(30_000L)
            timestamp = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault()).format(Date())
        }
    }

    val watermarkText = remember(userName, userId, timestamp) {
        if (userId.isNotEmpty()) {
            "$userName ($userId) • $timestamp"
        } else {
            "$userName • $timestamp"
        }
    }

    val textColor = MaterialTheme.colorScheme.onSurface.copy(alpha = alpha)

    Canvas(
        modifier = modifier.fillMaxSize()
    ) {
        val paint = Paint().apply {
            color = textColor.toArgb()
            textSize = 34f
            typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
            isAntiAlias = true
        }

        val stepX = 480f
        val stepY = 280f

        val width = size.width
        val height = size.height

        drawIntoCanvas { canvas ->
            val native = canvas.nativeCanvas
            var y = -100f
            var rowIndex = 0
            while (y < height + 200f) {
                // Offset alternating rows for a balanced diagonal pattern
                val xOffset = if (rowIndex % 2 == 0) 0f else stepX / 2f
                var x = -150f + xOffset
                while (x < width + 200f) {
                    native.save()
                    native.rotate(-28f, x, y)
                    native.drawText(watermarkText, x, y, paint)
                    native.restore()
                    x += stepX
                }
                y += stepY
                rowIndex++
            }
        }
    }
}
