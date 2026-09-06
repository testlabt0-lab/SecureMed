package com.securemed.app.data.api

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import retrofit2.HttpException

/**
 * Turns a failed request into the message the server actually sent.
 *
 * Without this, every API failure reaches the user as Retrofit's
 * `HttpException.message` — "HTTP 400 Bad Request" — while the backend's own
 * Arabic explanation sits unread in the error body. That is how a wrong 2FA
 * code and an expired 2FA token became the same unhelpful string.
 *
 * DRF error bodies come in three shapes, so all three are handled:
 *   {"detail": "رمز التحقق غير صحيح"}          — APIView / permission failures
 *   {"code": ["This field is required."]}       — serializer field errors
 *   ["Some non-field error"]                    — bare list
 */
object ApiErrors {

    private val json = Json { ignoreUnknownKeys = true }

    /** HTTP status the backend uses for an expired/unknown `mfa_token`. */
    const val UNAUTHORIZED = 401

    /** The response status, or null when the failure never reached the server. */
    fun statusOf(throwable: Throwable): Int? = (throwable as? HttpException)?.code()

    /**
     * The server's message for [throwable], or [fallback] when there is none.
     *
     * Never returns a raw status line: a 500 with an HTML body, a timeout, or a
     * TLS failure all fall through to [fallback], because none of those carry
     * anything a user can act on.
     */
    fun messageFor(throwable: Throwable, fallback: String): String {
        val http = throwable as? HttpException ?: return throwable.localizedMessage ?: fallback
        // errorBody() is a one-shot stream; string() consumes and closes it.
        val body = runCatching { http.response()?.errorBody()?.string() }.getOrNull()
        if (body.isNullOrBlank()) return fallback
        return runCatching { extract(json.parseToJsonElement(body)) }.getOrNull()?.takeIf {
            it.isNotBlank()
        } ?: fallback
    }

    private fun extract(element: kotlinx.serialization.json.JsonElement): String? = when (element) {
        is JsonPrimitive -> element.contentOrNullIfNotString()

        is JsonArray -> element.firstNotNullOfOrNull { extract(it) }

        is JsonObject -> {
            // `detail` first — it is the one DRF uses for the human-facing
            // message. Only then fall back to whichever field failed, so a
            // field error still says something rather than nothing.
            //
            // The missing key must stay null rather than becoming an empty
            // JsonObject: recursing into that stand-in re-entered this branch
            // with another empty object every time, and the StackOverflowError
            // was swallowed by the runCatching in messageFor — which is how
            // every field error came out as the generic fallback.
            element["detail"]?.let { extract(it) }
                ?: element.values.firstNotNullOfOrNull { extract(it) }
        }

        else -> null
    }

    /**
     * Guards against reporting a serialized `true` or `404` as an error message:
     * `requires_2fa` and status codes are primitives too.
     */
    private fun JsonPrimitive.contentOrNullIfNotString(): String? =
        if (isString) content.takeIf { it.isNotBlank() } else null
}

/**
 * The 2FA challenge is no longer valid — its `mfa_token` aged out of the
 * server's cache (5 minutes) or was already spent.
 *
 * A distinct type because the recovery differs from every other 2FA error: a
 * wrong code should leave the user on the code screen to try again, while this
 * has to send them back to the login form, since only a fresh `auth/login/`
 * can mint a new token. Carrying it as a type keeps that decision in the
 * ViewModel without teaching it about HTTP status codes.
 */
class TwoFactorExpiredException(message: String) : Exception(message)
