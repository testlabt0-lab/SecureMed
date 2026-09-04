package com.securemed.app.data.paging

import androidx.paging.PagingSource
import com.securemed.app.data.api.SecureMedApi
import com.securemed.app.data.model.PagedResponse
import com.securemed.app.data.model.Patient
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Unit tests for PatientPagingSource.
 */
class PatientPagingSourceTest {

    private val api: SecureMedApi = mockk()
    private val pagingSource = PatientPagingSource(api)

    @Test
    fun `load returns Page when api call is successful`() = runBlocking {
        // Arrange
        val patients = listOf(
            Patient(id = "1", fullName = "Ali", email = "", nationalId = "", isHighRisk = false, createdAt = ""),
            Patient(id = "2", fullName = "Omar", email = "", nationalId = "", isHighRisk = true, createdAt = "")
        )
        val response = PagedResponse(
            count = 2,
            next = "http://api/patients/?page=2",
            previous = null,
            results = patients
        )
        coEvery { api.getPatients() } returns response

        // Act
        val result = pagingSource.load(
            PagingSource.LoadParams.Refresh(
                key = 1,
                loadSize = 20,
                placeholdersEnabled = false
            )
        )

        // Assert
        assertTrue(result is PagingSource.LoadResult.Page)
        val page = result as PagingSource.LoadResult.Page
        assertEquals(2, page.data.size)
        assertEquals(2, page.nextKey) // Since next != null and position was 1
        assertEquals(null, page.prevKey)
    }

    @Test
    fun `load returns Error when api call fails`() = runBlocking {
        // Arrange
        val exception = RuntimeException("Network Error")
        coEvery { api.getPatients() } throws exception

        // Act
        val result = pagingSource.load(
            PagingSource.LoadParams.Refresh(
                key = 1,
                loadSize = 20,
                placeholdersEnabled = false
            )
        )

        // Assert
        assertTrue(result is PagingSource.LoadResult.Error)
        val error = result as PagingSource.LoadResult.Error
        assertEquals(exception, error.throwable)
    }
}
