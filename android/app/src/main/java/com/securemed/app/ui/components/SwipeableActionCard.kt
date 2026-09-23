package com.securemed.app.ui.components

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.unit.dp

/**
 * Interactive Swipe-Action wrapper for Appointment and Patient cards.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SwipeableActionCard(
    modifier: Modifier = Modifier,
    startActionIcon: ImageVector = Icons.Default.Phone,
    startActionText: String = "اتصال",
    startActionColor: Color = Color(0xFF16A34A), // Green
    onStartAction: () -> Unit = {},
    endActionIcon: ImageVector = Icons.Default.Check,
    endActionText: String = "إجراء",
    endActionColor: Color = Color(0xFF2563EB), // Blue
    onEndAction: () -> Unit = {},
    content: @Composable () -> Unit
) {
    val haptic = LocalHapticFeedback.current
    var hasHapticFired by remember { mutableStateOf(false) }

    val dismissState = rememberSwipeToDismissBoxState(
        confirmValueChange = { value ->
            when (value) {
                SwipeToDismissBoxValue.StartToEnd -> {
                    haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                    onStartAction()
                    false // Don't dismiss off screen, just trigger action
                }
                SwipeToDismissBoxValue.EndToStart -> {
                    haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                    onEndAction()
                    false // Don't dismiss off screen, just trigger action
                }
                SwipeToDismissBoxValue.Settled -> {
                    hasHapticFired = false
                    true
                }
            }
        },
        positionalThreshold = { totalDistance -> totalDistance * 0.35f }
    )

    SwipeToDismissBox(
        state = dismissState,
        modifier = modifier.clip(RoundedCornerShape(12.dp)),
        backgroundContent = {
            val direction = dismissState.dismissDirection

            val backgroundColor by animateColorAsState(
                targetValue = when (direction) {
                    SwipeToDismissBoxValue.StartToEnd -> startActionColor
                    SwipeToDismissBoxValue.EndToStart -> endActionColor
                    else -> Color.Transparent
                },
                label = "swipe_bg"
            )

            val icon = when (direction) {
                SwipeToDismissBoxValue.StartToEnd -> startActionIcon
                SwipeToDismissBoxValue.EndToStart -> endActionIcon
                else -> null
            }

            val label = when (direction) {
                SwipeToDismissBoxValue.StartToEnd -> startActionText
                SwipeToDismissBoxValue.EndToStart -> endActionText
                else -> ""
            }

            val iconScale by animateFloatAsState(
                targetValue = if (direction != SwipeToDismissBoxValue.Settled) 1.2f else 0.8f,
                label = "icon_scale"
            )

            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(backgroundColor)
                    .padding(horizontal = 20.dp),
                contentAlignment = if (direction == SwipeToDismissBoxValue.StartToEnd) Alignment.CenterStart else Alignment.CenterEnd
            ) {
                if (icon != null) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(
                            imageVector = icon,
                            contentDescription = label,
                            tint = Color.White,
                            modifier = Modifier.scale(iconScale)
                        )
                        Text(
                            text = label,
                            color = Color.White,
                            style = MaterialTheme.typography.labelLarge
                        )
                    }
                }
            }
        }
    ) {
        content()
    }
}
