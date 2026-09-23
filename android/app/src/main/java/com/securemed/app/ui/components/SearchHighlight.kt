package com.securemed.app.ui.components

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow

/**
 * Builds an AnnotatedString highlighting all occurrences of [query] in [text].
 */
fun buildHighlightedText(
    text: String,
    query: String,
    highlightColor: Color,
    textColor: Color,
    highlightTextColor: Color = textColor
): AnnotatedString {
    if (query.isBlank()) {
        return AnnotatedString(text)
    }

    return buildAnnotatedString {
        val lowerText = text.lowercase()
        val lowerQuery = query.trim().lowercase()
        var startIndex = 0

        while (startIndex < text.length) {
            val index = lowerText.indexOf(lowerQuery, startIndex)
            if (index == -1) {
                append(text.substring(startIndex))
                break
            }

            if (index > startIndex) {
                append(text.substring(startIndex, index))
            }

            val endIndex = index + lowerQuery.length
            val matchedText = text.substring(index, endIndex)

            pushStyle(
                SpanStyle(
                    background = highlightColor,
                    color = highlightTextColor,
                    fontWeight = FontWeight.Bold
                )
            )
            append(matchedText)
            pop()

            startIndex = endIndex
        }
    }
}

/**
 * High-performance text composable that highlights search terms instantly.
 */
@Composable
fun HighlightedText(
    text: String,
    query: String,
    modifier: Modifier = Modifier,
    style: TextStyle = MaterialTheme.typography.bodyMedium,
    color: Color = MaterialTheme.colorScheme.onSurface,
    highlightColor: Color = MaterialTheme.colorScheme.primaryContainer,
    highlightTextColor: Color = MaterialTheme.colorScheme.onPrimaryContainer,
    maxLines: Int = Int.MAX_VALUE,
    overflow: TextOverflow = TextOverflow.Clip
) {
    val annotatedString = buildHighlightedText(
        text = text,
        query = query,
        highlightColor = highlightColor,
        textColor = color,
        highlightTextColor = highlightTextColor
    )

    Text(
        text = annotatedString,
        modifier = modifier,
        style = style,
        color = color,
        maxLines = maxLines,
        overflow = overflow
    )
}
