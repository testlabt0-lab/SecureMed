package com.securemed.app.ui.screens

import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.paging.PatientPagingSource
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Before
import org.junit.Test

/**
 * Unit tests for [PatientsViewModel].
 */
@OptIn(ExperimentalCoroutinesApi::class)
class PatientsViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var repository: SecureMedRepository
    private lateinit var viewModel: PatientsViewModel
    private lateinit var pagingSource: PatientPagingSource

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        repository = mockk(relaxed = true)
        pagingSource = mockk(relaxed = true)
        every { repository.getPatientPagingSource() } returns pagingSource

        viewModel = PatientsViewModel(repository)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    /**
     * `Pager` invokes `pagingSourceFactory` per generation, on collection —
     * never at construction. The previous version of this test asserted the
     * opposite ("Pager is initialized eagerly"), read the flow into an unused
     * local, and failed. Pinning the laziness makes the next test meaningful.
     */
    @Test
    fun `constructing the ViewModel does not query the repository`() {
        verify(exactly = 0) { repository.getPatientPagingSource() }
    }

    @Test
    fun `collecting patientsPagingFlow asks the repository for a PagingSource`() {
        // Collected on the test dispatcher rather than inside runTest: cachedIn
        // parks a long-lived coroutine in viewModelScope that outlives the test
        // body, which runTest would report as an unfinished coroutine.
        // runCatching keeps any downstream Paging failure from reaching the
        // scope's uncaught-exception handler — the factory call is already
        // recorded by then.
        val collector = CoroutineScope(testDispatcher).launch {
            runCatching { viewModel.patientsPagingFlow.collect { } }
        }
        testDispatcher.scheduler.advanceUntilIdle()

        verify(atLeast = 1) { repository.getPatientPagingSource() }
        collector.cancel()
    }
}
