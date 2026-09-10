package com.securemed.app.ui.screens

import com.securemed.app.data.SecureMedRepository
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * Unit tests for the self-service account deletion flow (4-3 §2).
 *
 * The states that matter to the caller: `deleted = true` only after a
 * successful server round-trip (the local wipe happens inside the repository
 * call — wiping on failure would tell the user "deleted" while the account
 * lives), and failure surfaces the server's message with the dialog still
 * open.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class DeleteAccountViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var repository: SecureMedRepository
    private lateinit var viewModel: DeleteAccountViewModel

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        repository = mockk(relaxed = true)
        viewModel = DeleteAccountViewModel(repository)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `successful deletion sets deleted for navigation`() = runTest(testDispatcher) {
        coEvery { repository.deleteAccount("correct-pass") } returns Result.success(Unit)

        viewModel.deleteAccount("correct-pass")
        advanceUntilIdle()

        assertTrue(viewModel.uiState.value.deleted)
        assertFalse(viewModel.uiState.value.inProgress)
    }

    @Test
    fun `failure keeps the dialog open with the server message`() = runTest(testDispatcher) {
        coEvery { repository.deleteAccount("wrong-pass") } returns Result.failure(
            RuntimeException("كلمة المرور غير صحيحة")
        )

        viewModel.deleteAccount("wrong-pass")
        advanceUntilIdle()

        assertFalse(viewModel.uiState.value.deleted)
        assertFalse(viewModel.uiState.value.inProgress)
        assertTrue(viewModel.uiState.value.message?.contains("كلمة المرور") == true)
    }

    @Test
    fun `in-progress clears even when the call fails`() = runTest(testDispatcher) {
        coEvery { repository.deleteAccount(any()) } returns Result.failure(RuntimeException("network"))

        viewModel.deleteAccount("x")
        advanceUntilIdle()

        assertFalse(viewModel.uiState.value.inProgress)
    }

    @Test
    fun `clearMessage empties the error but not the deleted flag`() = runTest(testDispatcher) {
        coEvery { repository.deleteAccount(any()) } returns Result.success(Unit)

        viewModel.deleteAccount("pass")
        advanceUntilIdle()

        viewModel.clearMessage()

        // Navigation flag must survive a message clear — the screen reads it
        // in a LaunchedEffect that may run after the user taps something.
        assertTrue(viewModel.uiState.value.deleted)
    }
}
