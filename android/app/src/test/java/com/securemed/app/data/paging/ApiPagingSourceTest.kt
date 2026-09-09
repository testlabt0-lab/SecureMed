package com.securemed.app.data.paging

import androidx.paging.PagingSource
import com.securemed.app.data.api.SecureMedApi
import com.securemed.app.data.model.Appointment
import com.securemed.app.data.model.PagedResponse
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Unit tests for [ApiPagingSource] — the generic source behind the lab,
 * appointments, telemedicine, prescriptions, notifications and users lists.
 *
 * The contract under test is the same one [PatientPagingSourceTest] pins for
 * patients: the next key comes from the envelope's `has_next`, so a page
 * reporting more data must hand Paging the following page number and the
 * last page must hand it null or the list scrolls forever.
 */
class ApiPagingSourceTest {

    private val api: SecureMedApi = mockk()

    private fun appointment(id: String) = Appointment(id = id, patientName = "مريض $id")

    private fun refresh(key: Int) = PagingSource.LoadParams.Refresh<Int>(
        key = key,
        loadSize = 20,
        placeholdersEnabled = false
    )

    @Test
    fun `load returns Page and derives next key from has_next`() = runBlocking {
        val source = ApiPagingSource<Appointment> { page ->
            coEvery { api.getAppointments(page = 1) } returns PagedResponse(
                count = 3,
                page = 1,
                totalPages = 2,
                hasNext = true,
                hasPrevious = false,
                results = listOf(appointment("1"), appointment("2"))
            )
            api.getAppointments(page = page)
        }

        val result = source.load(refresh(1))

        assertTrue(result is PagingSource.LoadResult.Page)
        val page = result as PagingSource.LoadResult.Page
        assertEquals(2, page.data.size)
        assertEquals(2, page.nextKey)
        assertEquals(null, page.prevKey)
    }

    @Test
    fun `load stops paging on the last page`() = runBlocking {
        val source = ApiPagingSource<Appointment> { page ->
            coEvery { api.getAppointments(page = 2) } returns PagedResponse(
                count = 3,
                page = 2,
                totalPages = 2,
                hasNext = false,
                hasPrevious = true,
                results = listOf(appointment("3"))
            )
            api.getAppointments(page = page)
        }

        val result = source.load(refresh(2))

        val page = result as PagingSource.LoadResult.Page
        assertEquals(1, page.data.size)
        assertEquals(null, page.nextKey)
        assertEquals(1, page.prevKey)
    }

    @Test
    fun `load returns Error when the page request fails`() = runBlocking {
        val exception = RuntimeException("Network Error")
        val source = ApiPagingSource<Appointment> { _ ->
            throw exception
        }

        val result = source.load(refresh(1))

        assertTrue(result is PagingSource.LoadResult.Error)
        assertEquals(exception, (result as PagingSource.LoadResult.Error).throwable)
    }
}
