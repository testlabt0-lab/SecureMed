package com.securemed.app.hardware.voice

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.MicOff
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat

@Composable
fun VoiceInputButton(
    modifier: Modifier = Modifier,
    onTextSpoken: (String) -> Unit
) {
    val context = LocalContext.current
    val haptic = LocalHapticFeedback.current
    val speechHelper = remember { SpeechRecognitionHelper(context) }
    val isListening by speechHelper.isListening.collectAsState()
    val rmsDb by speechHelper.rmsDb.collectAsState()

    DisposableEffect(Unit) {
        onDispose {
            speechHelper.destroy()
        }
    }

    var hasMicPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.RECORD_AUDIO
            ) == PackageManager.PERMISSION_GRANTED
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { granted ->
        hasMicPermission = granted
        if (granted) {
            haptic.performHapticFeedback(HapticFeedbackType.LongPress)
            speechHelper.startListening(
                onFinalResult = { text ->
                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                    onTextSpoken(text)
                }
            )
        }
    }

    // Pulsing scale animation when listening
    val pulseScale by animateFloatAsState(
        targetValue = if (isListening) 1f + (rmsDb.coerceIn(0f, 10f) / 20f) else 1f,
        animationSpec = spring(stiffness = Spring.StiffnessLow),
        label = "mic_pulse"
    )

    val buttonColor by animateColorAsState(
        targetValue = if (isListening) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
        label = "mic_color"
    )

    Box(
        modifier = modifier,
        contentAlignment = Alignment.Center
    ) {
        if (isListening) {
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .scale(pulseScale * 1.3f)
                    .background(buttonColor.copy(alpha = 0.25f), CircleShape)
            )
        }

        IconButton(
            onClick = {
                if (!hasMicPermission) {
                    permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                } else {
                    if (isListening) {
                        haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                        speechHelper.stopListening()
                    } else {
                        haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                        speechHelper.startListening(
                            onFinalResult = { text ->
                                haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                onTextSpoken(text)
                            }
                        )
                    }
                }
            },
            modifier = Modifier.size(36.dp)
        ) {
            Icon(
                imageVector = if (isListening) Icons.Default.Mic else Icons.Default.MicOff,
                contentDescription = if (isListening) "جاري الاستماع... اضغط للإيقاف" else "اضغط للإملاء الصوتي الطبي",
                tint = buttonColor,
                modifier = Modifier.size(20.dp)
            )
        }
    }
}
