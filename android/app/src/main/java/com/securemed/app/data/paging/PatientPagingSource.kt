package com.securemed.app.data.paging

import androidx.paging.PagingSource
import androidx.paging.PagingState
import com.securemed.app.data.api.SecureMedApi
import com.securemed.app.data.model.Patient

class PatientPagingSource(
    private val api: SecureMedApi
) : PagingSource<Int, Patient>() {

    override suspend fun load(params: LoadParams<Int>): LoadResult<Int, Patient> {
        val position = params.key ?: 1
        return try {
            val response = api.getPatients(page = position)
            val patients = response.results
            
            // To simulate pagination for the demo, we check if we have more pages (next != null)
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
