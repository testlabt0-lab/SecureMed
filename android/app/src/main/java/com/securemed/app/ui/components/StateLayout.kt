package com.securemed.app.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

@Composable
fun StateLayout(
    isLoading: Boolean,
    isError: Boolean,
    errorMessage: String? = null,
    isEmpty: Boolean = false,
    emptyMessage: String = "لا توجد بيانات لعرضها",
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit
) {
    Box(modifier = modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        when {
            // Loading state
            isLoading -> {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    CircularProgressIndicator()
                    Spacer(modifier = Modifier.height(12.dp))
                    Text("جاري التحميل...", style = MaterialTheme.typography.bodyMedium)
                }
            }
            // Error state
            isError -> {
                Column(
                    modifier = Modifier.padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = errorMessage ?: "حدث خطأ غير متوقع",
                        style = MaterialTheme.typography.bodyLarge,
                        textAlign = TextAlign.Center,
                        color = MaterialTheme.colorScheme.error
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Button(onClick = onRetry) {
                        Text("إعادة المحاولة")
                    }
                }
            }
            // Empty state
            isEmpty -> {
                Text(
                    text = emptyMessage,
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            // Success state
            else -> {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.TopStart) {
                    content()
                }
            }
        }
    }
}
