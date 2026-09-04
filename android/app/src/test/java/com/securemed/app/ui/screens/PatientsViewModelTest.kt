package com.securemed.app.ui.screens

import androidx.paging.PagingData
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.paging.PatientPagingSource
import io.mockk.mockk
import io.mockk.verify
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Before
import org.junit.Test

/**
 * Unit tests for PatientsViewModel.
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

        // Arrange
        io.mockk.every { repository.getPatientPagingSource() } returns pagingSource

        viewModel = PatientsViewModel(repository)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `patientsPagingFlow retrieves PagingSource from repository`() {
        // Since Pager is initialized eagerly in the ViewModel,
        // it should call getPatientPagingSource at least once when the flow is collected.
        // For simple verification, we verify if the repository was interacted with.
        
        // Act
        val flow = viewModel.patientsPagingFlow
        
        // Assert
        verify { repository.getPatientPagingSource() }
    }
}
