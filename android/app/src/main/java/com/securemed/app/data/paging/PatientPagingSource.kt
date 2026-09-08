package com.securemed.app.data.paging

import androidx.paging.PagingSource
import androidx.paging.PagingState
import com.securemed.app.data.api.SecureMedApi
import com.securemed.app.data.model.Patient

/**
 * Pages the patient list, optionally through a server-side search term.
 *
 * [search] flows through every page request — a query that only filtered
 * page 1 would show the matches of the first 20 patients and then append
 * unrelated ones as the user scrolls. A new [Search] value must produce a
 * new PagingSource (the ViewModel recreates it), because a PagingSource is
 * immutable once loading begins.
 */
class PatientPagingSource(
    private val api: SecureMedApi,
    private val search: String? = null
) : PagingSource<Int, Patient>() {

    /** Tag so a stale source can refuse to answer after the term changed. */
    data class Search(val term: String?) {
        val pagingKey: String get() = term?.trim().orEmpty()
    }

    override suspend fun load(params: LoadParams<Int>): LoadResult<Int, Patient> {
        val position = params.key ?: 1
        return try {
            val response = api.getPatients(
                page = position,
                search = search?.takeIf { it.isNotBlank() }
            )
            val patients = response.results

            val nextKey = if (response.hasNext) position + 1 else null

            LoadResult.Page(
                data = patients,
                prevKey = if (position == 1) null else position - 1,
                nextKey = nextKey
            )
        } catch (e: Exception) {
            LoadResult.Error(e)
        }
    }

    override fun getRefreshKey(state: PagingState<Int, Patient>): Int? {
        return state.anchorPosition?.let { anchorPosition ->
            state.closestPageToPosition(anchorPosition)?.prevKey?.plus(1)
                ?: state.closestPageToPosition(anchorPosition)?.nextKey?.minus(1)
        }
    }
}
