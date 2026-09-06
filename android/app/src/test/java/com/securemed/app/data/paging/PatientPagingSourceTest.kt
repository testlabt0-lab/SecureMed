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
 * Unit tests for [PatientPagingSource].
 *
 * Paging keys are derived from the backend envelope's `has_next` flag, not
 * from a `next` URL, so these tests pin that mapping: a page that reports
 * more data must hand Paging the following page number, and the last page
 * must hand it null or the list scrolls forever.
 */
class PatientPagingSourceTest {

    private val api: SecureMedApi = mockk()
    private val pagingSource = PatientPagingSource(api)

    private fun patient(id: String, name: String) = Patient(
        id = id,
        fullName = name,
        dateOfBirth = "1990-01-01",
        gender = "MALE"
    )

    private fun refresh(key: Int) = PagingSource.LoadParams.Refresh(
        key = key,
        loadSize = 20,
        placeholdersEnabled = false
    )

    @Test
    fun `load returns Page when api call is successful`() = runBlocking {
        // Arrange
        val patients = listOf(patient("1", "Ali"), patient("2", "Omar"))
        coEvery { api.getPatients(page = 1) } returns PagedResponse(
            count = 4,
            page = 1,
            totalPages = 2,
            hasNext = true,
            hasPrevious = false,
            results = patients
        )

        // Act
        val result = pagingSource.load(refresh(1))

        // Assert
        assertTrue(result is PagingSource.LoadResult.Page)
        val page = result as PagingSource.LoadResult.Page
        assertEquals(2, page.data.size)
        assertEquals(2, page.nextKey) // has_next == true and position was 1
        assertEquals(null, page.prevKey) // first page has nothing before it
    }

    @Test
    fun `load stops paging on the last page`() = runBlocking {
        // Arrange
        coEvery { api.getPatients(page = 2) } returns PagedResponse(
            count = 3,
            page = 2,
            totalPages = 2,
            hasNext = false,
            hasPrevious = true,
            results = listOf(patient("3", "Sara"))
        )

        // Act
        val result = pagingSource.load(refresh(2))

        // Assert
        val page = result as PagingSource.LoadResult.Page
        assertEquals(1, page.data.size)
        assertEquals(null, page.nextKey) // no further request may be issued
        assertEquals(1, page.prevKey)
    }

    @Test
    fun `load returns Error when api call fails`() = runBlocking {
        // Arrange
        val exception = RuntimeException("Network Error")
        coEvery { api.getPatients(page = 1) } throws exception

        // Act
        val result = pagingSource.load(refresh(1))

        // Assert
        assertTrue(result is PagingSource.LoadResult.Error)
        val error = result as PagingSource.LoadResult.Error
        assertEquals(exception, error.throwable)
    }
}
