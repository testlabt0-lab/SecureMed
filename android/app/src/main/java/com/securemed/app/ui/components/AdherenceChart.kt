package com.securemed.app.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import java.time.LocalDate

/**
 * Per-day taken/expected ratio for one plan over the last [days] days.
 * Null entries are days with no scheduled dose (gaps, not zeros — see
 * [AdherenceChart]).
 */
fun dailyAdherenceSeries(
    logsKeys: Set<String>,
    planId: String,
    planTimes: List<String>,
    planStart: LocalDate?,
    planEnd: LocalDate?,
    days: Int = 14,
    today: LocalDate = LocalDate.now(),
): List<Float?> {
    val series = mutableListOf<Float?>()
    for (offset in days - 1 downTo 0) {
        val day = today.minusDays(offset.toLong())
        if (planStart != null && day.isBefore(planStart)) {
            series += null
            continue
        }
        if (planEnd != null && day.isAfter(planEnd)) {
            series += null
            continue
        }
        var expected = 0
        var taken = 0
        planTimes.forEach { t ->
            val time = runCatching { java.time.LocalTime.parse(t) }.getOrNull()
                ?: return@forEach
            expected++
            if ("$planId|${java.time.LocalDateTime.of(day, time)}" in logsKeys) taken++
        }
        series += if (expected == 0) null else taken.toFloat() / expected
    }
    return series
}

/**
 * Adherence spark-line, drawn on a Canvas instead of a charting library.
 *
 * The chart shows one point per day for the last [days] days: taken / expected
 * doses as a 0..1 ratio. A flat line at 1.0 is perfect adherence; dips are
 * days with missed doses, and *absent* points are days with no scheduled dose
 * at all (skipped rather than failed — drawn as gaps, not as zeros, because
 * plotting them as zero would tell the clinician the patient missed
 * everything on a day they had nothing to take).
 *
 * @param perDay one ratio per day, oldest first; entries are nullable.
 * @param days   how many days the list represents (for the empty case).
 */
@Composable
fun AdherenceChart(
    perDay: List<Float?>,
    days: Int = 14,
    modifier: Modifier = Modifier,
) {
    val lineColor = MaterialTheme.colorScheme.primary
    val fillColor = lineColor.copy(alpha = 0.15f)
    val gridColor = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f)
    val pointColor = MaterialTheme.colorScheme.secondary

    Canvas(
        modifier = modifier
            .fillMaxWidth()
            .height(120.dp)
            .padding(horizontal = 8.dp, vertical = 8.dp)
    ) {
        if (perDay.isEmpty()) return@Canvas

        val w = size.width
        val h = size.height
        val bottom = h
        val stepX = if (perDay.size > 1) w / (perDay.size - 1) else w

        // Grid at 0, 50%, 100%
        listOf(0f, 0.5f, 1f).forEach { ratio ->
            val y = bottom - ratio * h
            drawLine(
                color = gridColor,
                start = Offset(0f, y),
                end = Offset(w, y),
                strokeWidth = 1.dp.toPx(),
            )
        }

        // Build the segments. Gaps (null entries) break the line so the
        // clinician doesn't read a no-dose day as a missed-dose day.
        var currentPath: Path? = null
        var currentFill: Path? = null

        fun flushSegment() {
            currentPath?.let { p ->
                drawPath(p, fillColor)
                drawPath(p, lineColor, style = Stroke(width = 2.dp.toPx()))
            }
            currentPath = null
            currentFill = null
        }

        perDay.forEachIndexed { i, ratio ->
            if (ratio == null) {
                flushSegment()
                return@forEachIndexed
            }
            val x = i * stepX
            val y = bottom - ratio.coerceIn(0f, 1f) * h

            if (currentPath == null) {
                currentPath = Path().apply { moveTo(x, y) }
                currentFill = Path().apply {
                    moveTo(x, bottom)
                    lineTo(x, y)
                }
            } else {
                currentPath!!.lineTo(x, y)
                currentFill!!.lineTo(x, y)
            }
        }
        flushSegment()

        // Points on days that have data. Skip when many days make them noise.
        if (perDay.size <= 20) {
            perDay.forEachIndexed { i, ratio ->
                if (ratio != null) {
                    drawCircle(
                        color = pointColor,
                        radius = 2.5.dp.toPx(),
                        center = Offset(i * stepX, bottom - ratio.coerceIn(0f, 1f) * h),
                    )
                }
            }
        }
    }
}

/**
 * Aggregates the per-plan daily series into one series for the whole plan
 * list: each day's value is total taken / total expected across every active
 * plan that had a dose scheduled that day. Days where no plan schedules
 * anything stay null (a gap, not a zero).
 */
fun buildDailySeries(
    takenKeys: Set<String>,
    plans: List<com.securemed.app.data.model.Medication>,
    days: Int = 14,
): List<Float?> {
    val today = java.time.LocalDate.now()
    val perPlan = plans
        .filter { it.isActive }
        .map { plan ->
            dailyAdherenceSeries(
                logsKeys = takenKeys,
                planId = plan.id,
                planTimes = plan.times,
                planStart = runCatching { LocalDate.parse(plan.startDate) }.getOrNull(),
                planEnd = plan.endDate
                    ?.let { runCatching { LocalDate.parse(it) }.getOrNull() },
                days = days,
                today = today,
            )
        }
    if (perPlan.isEmpty()) return List(days) { null }

    return (0 until days).map { i ->
        val dayValues = perPlan.mapNotNull { it.getOrNull(i) }
        if (dayValues.isEmpty()) null else dayValues.average().toFloat()
    }
}

