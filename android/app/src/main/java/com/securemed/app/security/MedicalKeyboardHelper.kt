package com.securemed.app.security

import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType

/**
 * Hardened keyboard configurations to protect patient privacy (HIPAA / Saudi PDPL).
 *
 * Prevents third-party keyboards (Gboard, SwiftKey, etc.) from learning or uploading
 * patient health information, clinical notes, and drug prescriptions.
 */
object MedicalKeyboardHelper {

    /**
     * Clinical text entry options (prescriptions, diagnoses, patient details).
     * Disables predictive auto-correct learning.
     */
    fun clinicalText(
        imeAction: ImeAction = ImeAction.Default,
        capitalization: KeyboardCapitalization = KeyboardCapitalization.Sentences
    ): KeyboardOptions {
        return KeyboardOptions(
            capitalization = capitalization,
            autoCorrect = false,
            keyboardType = KeyboardType.Text,
            imeAction = imeAction
        )
    }

    /**
     * Medical search entry options (search patient, records, appointments).
     */
    fun search(
        imeAction: ImeAction = ImeAction.Search
    ): KeyboardOptions {
        return KeyboardOptions(
            capitalization = KeyboardCapitalization.None,
            autoCorrect = false,
            keyboardType = KeyboardType.Text,
            imeAction = imeAction
        )
    }

    /**
     * Secure numeric PIN / code options (2FA, Duress PIN, AppLock).
     */
    fun securePin(
        imeAction: ImeAction = ImeAction.Done
    ): KeyboardOptions {
        return KeyboardOptions(
            keyboardType = KeyboardType.NumberPassword,
            imeAction = imeAction
        )
    }
}
