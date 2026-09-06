package com.securemed.app.data.api

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import retrofit2.HttpException
import retrofit2.Response
import java.io.IOException

/**
 * Unit tests for [ApiErrors].
 *
 * The behaviour under test is what the user reads after a failed request, so
 * each case is one of the shapes the backend actually returns.
 */
class ApiErrorsTest {

    private val fallback = "تعذر تنفيذ الطلب"

    private fun httpError(status: Int, body: String, contentType: String = "application/json") =
        HttpException(
            Response.error<Any>(status, body.toResponseBody(contentType.toMediaType()))
        )

    @Test
    fun `reads the detail an APIView returned`() {
        val error = httpError(400, """{"detail":"رمز التحقق غير صحيح"}""")

        assertEquals("رمز التحقق غير صحيح", ApiErrors.messageFor(error, fallback))
    }

    @Test
    fun `reads the first message out of serializer field errors`() {
        val error = httpError(400, """{"code":["هذا الحقل مطلوب"]}""")

        assertEquals("هذا الحقل مطلوب", ApiErrors.messageFor(error, fallback))
    }

    @Test
    fun `reads a bare list of non-field errors`() {
        val error = httpError(400, """["بيانات الدخول غير صحيحة"]""")

        assertEquals("بيانات الدخول غير صحيحة", ApiErrors.messageFor(error, fallback))
    }

    @Test
    fun `prefers detail over any other field`() {
        val error = httpError(400, """{"code":["حقل"],"detail":"رسالة"}""")

        assertEquals("رسالة", ApiErrors.messageFor(error, fallback))
    }

    /**
     * A 500 behind a proxy comes back as an HTML page. Reporting a fragment of
     * it would be worse than the fallback, which at least reads as a sentence.
     */
    @Test
    fun `falls back for a body that is not JSON`() {
        val error = httpError(500, "<html><body>Server Error</body></html>", "text/html")

        assertEquals(fallback, ApiErrors.messageFor(error, fallback))
    }

    /**
     * `requires_2fa` and status codes are JSON primitives too — without the
     * is-string guard the user would be shown "true".
     */
    @Test
    fun `falls back when the body holds no strings`() {
        val error = httpError(400, """{"requires_2fa":true,"status":404}""")

        assertEquals(fallback, ApiErrors.messageFor(error, fallback))
    }

    @Test
    fun `falls back for an empty body`() {
        val error = httpError(401, "")

        assertEquals(fallback, ApiErrors.messageFor(error, fallback))
    }

    @Test
    fun `falls back for a whitespace-only detail`() {
        val error = httpError(400, """{"detail":"   "}""")

        assertEquals(fallback, ApiErrors.messageFor(error, fallback))
    }

    /**
     * A timeout or a DNS failure never reached the server, so there is no body;
     * the exception's own message is the most specific thing available.
     */
    @Test
    fun `uses the exception message when the request never reached the server`() {
        val error = IOException("timeout")

        assertEquals("timeout", ApiErrors.messageFor(error, fallback))
    }

    @Test
    fun `statusOf reports the HTTP status`() {
        assertEquals(401, ApiErrors.statusOf(httpError(401, """{"detail":"انتهت"}""")))
    }

    @Test
    fun `statusOf is null for a non-HTTP failure`() {
        assertNull(ApiErrors.statusOf(IOException("offline")))
    }
}
