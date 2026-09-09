package com.securemed.app.data.paging

import androidx.paging.PagingSource
import androidx.paging.PagingState
import com.securemed.app.data.model.PagedResponse

/**
 * A paged API list in one reusable source: [loadPage] fetches one page number
 * and the backend envelope (`has_next`) decides whether another page exists.
 *
 * This is the generic sibling of [PatientPagingSource] — same key mapping,
 * same failure contract (the raw throwable reaches `LoadState.Error` so the
 * screen can surface the server's message). The screen constructs one per
 * list via the repository's paging factories; a PagingSource is immutable
 * once loading begins, so any query change means a new factory call.
 */
class ApiPagingSource<T : Any>(
    private val loadPage: suspend (page: Int) -> PagedResponse<T>
) : PagingSource<Int, T>() {

    override suspend fun load(params: LoadParams<Int>): LoadResult<Int, T> {
        val position = params.key ?: 1
        return try {
            val response = loadPage(position)
            LoadResult.Page(
                data = response.results,
                prevKey = if (position == 1) null else position - 1,
                nextKey = if (response.hasNext) position + 1 else null
            )
        } catch (e: Exception) {
            LoadResult.Error(e)
        }
    }

    override fun getRefreshKey(state: PagingState<Int, T>): Int? {
        return state.anchorPosition?.let { anchorPosition ->
            state.closestPageToPosition(anchorPosition)?.prevKey?.plus(1)
                ?: state.closestPageToPosition(anchorPosition)?.nextKey?.minus(1)
        }
    }
}
