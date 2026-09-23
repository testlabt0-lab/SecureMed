package com.securemed.app.hardware.voice

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.Locale

/**
 * Speech-to-Text manager for medical dictation.
 * Supports Arabic with English fallback and sound level monitoring.
 */
class SpeechRecognitionHelper(private val context: Context) {

    private var speechRecognizer: SpeechRecognizer? = null

    private val _isListening = MutableStateFlow(false)
    val isListening: StateFlow<Boolean> = _isListening.asStateFlow()

    private val _rmsDb = MutableStateFlow(0f)
    val rmsDb: StateFlow<Float> = _rmsDb.asStateFlow()

    private val _lastRecognizedText = MutableStateFlow<String?>(null)
    val lastRecognizedText: StateFlow<String?> = _lastRecognizedText.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    fun isAvailable(): Boolean = SpeechRecognizer.isRecognitionAvailable(context)

    fun startListening(
        preferredLanguage: String = "ar-SA",
        onPartialResult: (String) -> Unit = {},
        onFinalResult: (String) -> Unit = {}
    ) {
        if (!isAvailable()) {
            _errorMessage.value = "التعرف الصوتي غير متاح على هذا الجهاز"
            return
        }

        stopListening()

        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(context).apply {
            setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) {
                    _isListening.value = true
                    _errorMessage.value = null
                }

                override fun onBeginningOfSpeech() = Unit

                override fun onRmsChanged(rmsdB: Float) {
                    _rmsDb.value = rmsdB
                }

                override fun onBufferReceived(buffer: ByteArray?) = Unit

                override fun onEndOfSpeech() {
                    _isListening.value = false
                }

                override fun onError(error: Int) {
                    _isListening.value = false
                    val msg = when (error) {
                        SpeechRecognizer.ERROR_NO_MATCH -> "لم يتم التعرف على الصوت"
                        SpeechRecognizer.ERROR_NETWORK -> "خطأ في الاتصال بشبكة التعرف الصوتي"
                        SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "انتهى وقت الاستماع بدون صوت"
                        SpeechRecognizer.ERROR_AUDIO -> "خطأ في تسجيل الصوت"
                        SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "إذن الميكروفون غير ممنوح"
                        else -> "حدث خطأ أثناء الاستماع"
                    }
                    _errorMessage.value = msg
                }

                override fun onResults(results: Bundle?) {
                    _isListening.value = false
                    val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    val text = matches?.firstOrNull()
                    if (!text.isNullOrBlank()) {
                        _lastRecognizedText.value = text
                        onFinalResult(text)
                    }
                }

                override fun onPartialResults(partialResults: Bundle?) {
                    val matches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    val text = matches?.firstOrNull()
                    if (!text.isNullOrBlank()) {
                        onPartialResult(text)
                    }
                }

                override fun onEvent(eventType: Int, params: Bundle?) = Unit
            })
        }

        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(
                RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
            )
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, preferredLanguage)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, preferredLanguage)
            putExtra(RecognizerIntent.EXTRA_ONLY_RETURN_LANGUAGE_PREFERENCE, preferredLanguage)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
        }

        try {
            speechRecognizer?.startListening(intent)
        } catch (e: Exception) {
            _isListening.value = false
            _errorMessage.value = e.localizedMessage
        }
    }

    fun stopListening() {
        try {
            speechRecognizer?.stopListening()
            speechRecognizer?.destroy()
        } catch (_: Exception) {}
        speechRecognizer = null
        _isListening.value = false
        _rmsDb.value = 0f
    }

    fun destroy() {
        stopListening()
    }
}
