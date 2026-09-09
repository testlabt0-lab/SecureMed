package com.securemed.app.data.model

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * The refresh contract (4-1, and the lesson of بند 2-7): a response body
 * without a `refresh` field must decode cleanly — the caller then keeps the
 * still-valid refresh token. An earlier decode-or-die shape treated that
 * body as a broken session and cleared the user out of the app.
 *
 * The three bodies below are the documented server behaviors on
 * `auth/refresh/`: rotation, no rotation, and a rejection.
 */
class RefreshContractTest {

    private val json = Json { ignoreUnknownKeys = true; coerceInputValues = true; encodeDefaults = true }

    @Test
    fun `rotated pair decodes and carries both tokens`() {
        val body = """
        {"access": "a2", "refresh": "r2"}
        """.trimIndent()

        val tokens = json.decodeFromString(RefreshResponse.serializer(), body)

        assertEquals("a2", tokens.access)
        assertEquals("r2", tokens.refresh)
    }

    @Test
    fun `unrotated access-only response decodes with a null refresh`() {
        // Exactly the body that used to be fatal: keep the old refresh token.
        val body = """{"access": "a3"}"""

        val tokens = json.decodeFromString(RefreshResponse.serializer(), body)

        assertEquals("a3", tokens.access)
        assertNull(tokens.refresh)
    }

    @Test
    fun `blank refresh string is decodable so the caller can skip it`() {
        // `tokens.refresh?.takeIf { it.isNotBlank() }` is the guard; the
        // decode itself must still succeed on an empty string.
        val body = """{"access": "a4", "refresh": ""}"""

        val tokens = json.decodeFromString(RefreshResponse.serializer(), body)

        assertEquals("a4", tokens.access)
        assertEquals("", tokens.refresh)
    }
}
