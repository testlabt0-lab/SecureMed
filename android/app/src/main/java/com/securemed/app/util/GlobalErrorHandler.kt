package com.securemed.app.util

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow

object GlobalErrorHandler {
    private val _errorFlow = MutableSharedFlow<String>(extraBufferCapacity = 1)
    val errorFlow = _errorFlow.asSharedFlow()

    fun emitError(message: String) {
        _errorFlow.tryEmit(message)
    }
}
