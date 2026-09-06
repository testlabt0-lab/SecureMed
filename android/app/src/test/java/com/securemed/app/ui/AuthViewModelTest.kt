package com.securemed.app.ui

import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.api.TwoFactorExpiredException
import com.securemed.app.data.model.LoginResponse
import com.securemed.app.data.model.TokenPair
import com.securemed.app.data.model.User
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * Unit tests for the two-factor half of [AuthViewModel].
 *
 * The distinction these pin down is which failures keep the user on the code
 * screen and which send them back to the login form: getting that wrong either
 * strands the user on a screen that can no longer succeed, or throws away a
 * still-valid code after one typo.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class AuthViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var repository: SecureMedRepository
    private lateinit var viewModel: AuthViewModel

    private val session = LoginResponse(
        tokens = TokenPair(access = "access", refresh = "refresh"),
        user = User(id = "1", email = "d@securemed.app", fullName = "طبيب", role = "doctor")
    )

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        repository = mockk(relaxed = true)
        viewModel = AuthViewModel(repository)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    private fun idle() = testDispatcher.scheduler.advanceUntilIdle()

    private fun arriveAtCodeScreen(method: String = "email", token: String = "tok") {
        coEvery { repository.login(any(), any()) } returns Result.success(
            LoginResponse(requiresTwoFactor = true, mfaToken = token, method = method)
        )
        viewModel.login("d@securemed.app", "pw")
        idle()
    }

    @Test
    fun `a requires_2fa login opens the code screen instead of failing`() {
        arriveAtCodeScreen(method = "totp", token = "tok-1")

        val state = viewModel.uiState.value as AuthUiState.AwaitingTwoFactor
        assertEquals("tok-1", state.mfaToken)
        assertEquals("totp", state.method)
        assertTrue(!state.submitting)
        assertNull(viewModel.errorMessage.value)
    }

    /**
     * `requires_2fa` with no token to answer it. Opening a code screen would
     * only produce a request that cannot succeed.
     */
    @Test
    fun `requires_2fa without an mfa_token is an error, not a code screen`() {
        coEvery { repository.login(any(), any()) } returns Result.success(
            LoginResponse(requiresTwoFactor = true, detail = "يجب إدخال رمز التحقق بخطوتين")
        )

        viewModel.login("d@securemed.app", "pw")
        idle()

        assertEquals(AuthUiState.Error, viewModel.uiState.value)
        assertEquals("يجب إدخال رمز التحقق بخطوتين", viewModel.errorMessage.value)
    }

    @Test
    fun `a correct code opens the session`() {
        arriveAtCodeScreen()
        coEvery { repository.mfaLogin(any(), any(), any()) } returns Result.success(session)

        viewModel.submitTwoFactorCode("123456")
        idle()

        assertTrue(viewModel.uiState.value is AuthUiState.Success)
    }

    /**
     * The server keeps `mfa_pending` alive after a wrong code, so the user must
     * stay where they are and retype — and must see the server's own wording.
     */
    @Test
    fun `a wrong code keeps the code screen and shows the server message`() {
        arriveAtCodeScreen()
        coEvery { repository.mfaLogin(any(), any(), any()) } returns
            Result.failure(Exception("رمز التحقق غير صحيح"))

        viewModel.submitTwoFactorCode("000000")
        idle()

        val state = viewModel.uiState.value as AuthUiState.AwaitingTwoFactor
        assertTrue(!state.submitting)
        assertEquals("رمز التحقق غير صحيح", viewModel.errorMessage.value)
    }

    /**
     * An expired token is the one failure that cannot be retried here: only a
     * fresh password login mints a new one.
     */
    @Test
    fun `an expired token returns to the login form`() {
        arriveAtCodeScreen()
        coEvery { repository.mfaLogin(any(), any(), any()) } returns
            Result.failure(TwoFactorExpiredException("انتهت صلاحية الجلسة، سجل الدخول من جديد"))

        viewModel.submitTwoFactorCode("123456")
        idle()

        assertEquals(AuthUiState.Error, viewModel.uiState.value)
        assertEquals("انتهت صلاحية الجلسة، سجل الدخول من جديد", viewModel.errorMessage.value)
    }

    @Test
    fun `the local countdown reaching zero returns to the login form`() {
        arriveAtCodeScreen()

        viewModel.expireTwoFactor()

        assertEquals(AuthUiState.Error, viewModel.uiState.value)
        assertEquals("انتهت مهلة رمز التحقق، سجّل الدخول من جديد", viewModel.errorMessage.value)
    }

    @Test
    fun `a blank code is not sent to the server`() {
        arriveAtCodeScreen()

        viewModel.submitTwoFactorCode("   ")
        idle()

        coVerify(exactly = 0) { repository.mfaLogin(any(), any(), any()) }
        assertTrue(viewModel.uiState.value is AuthUiState.AwaitingTwoFactor)
        assertEquals("أدخل رمز التحقق", viewModel.errorMessage.value)
    }

    /** Surrounding whitespace from a paste would fail the server's comparison. */
    @Test
    fun `the code is trimmed before it is sent`() {
        arriveAtCodeScreen(token = "tok-2")
        coEvery { repository.mfaLogin(any(), any(), any()) } returns Result.success(session)

        viewModel.submitTwoFactorCode(" 123456 ")
        idle()

        coVerify(exactly = 1) { repository.mfaLogin("tok-2", "123456", any()) }
    }

    /**
     * `trust_device` is what stops adaptive MFA mailing a code on every single
     * login (`DeviceRegistry.is_trusted` starts false), so a flag that is
     * dropped between the checkbox and the request would make the option a lie.
     */
    @Test
    fun `trusting the device forwards trust_device`() {
        arriveAtCodeScreen(token = "tok-3")
        coEvery { repository.mfaLogin(any(), any(), any()) } returns Result.success(session)

        viewModel.submitTwoFactorCode("123456", trustDevice = true)
        idle()

        coVerify(exactly = 1) { repository.mfaLogin("tok-3", "123456", true) }
    }

    /** Trusting a device is the user's decision, never a default. */
    @Test
    fun `trust_device is false unless it was asked for`() {
        arriveAtCodeScreen(token = "tok-4")
        coEvery { repository.mfaLogin(any(), any(), any()) } returns Result.success(session)

        viewModel.submitTwoFactorCode("123456")
        idle()

        coVerify(exactly = 1) { repository.mfaLogin("tok-4", "123456", false) }
    }

    @Test
    fun `submitting a code outside the code screen does nothing`() {
        viewModel.submitTwoFactorCode("123456")
        idle()

        coVerify(exactly = 0) { repository.mfaLogin(any(), any(), any()) }
        assertEquals(AuthUiState.Idle, viewModel.uiState.value)
    }

    @Test
    fun `going back clears the pending challenge`() {
        arriveAtCodeScreen()

        viewModel.cancelTwoFactor()

        assertEquals(AuthUiState.Idle, viewModel.uiState.value)
        assertNull(viewModel.errorMessage.value)
    }
}
