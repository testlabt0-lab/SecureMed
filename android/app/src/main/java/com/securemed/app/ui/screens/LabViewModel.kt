package com.securemed.app.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.cachedIn
import com.securemed.app.data.SecureMedRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

/**
 * Lab orders through real pagination (3-3): the Pager follows the server's
 * `has_next` envelope so long lists load as the user scrolls instead of
 * stopping at the first 20 rows.
 */
@HiltViewModel
class LabViewModel @Inject constructor(
    repository: SecureMedRepository
) : ViewModel() {

    val requestsPagingFlow = Pager(
        config = PagingConfig(pageSize = 20, enablePlaceholders = false),
        pagingSourceFactory = { repository.getLabOrdersPagingSource() }
    ).flow.cachedIn(viewModelScope)
}
