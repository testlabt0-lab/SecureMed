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
 * Telemedicine consultations through real pagination (3-3) — same Pager
 * contract as the lab and appointment lists: the server's `has_next` drives
 * loading as the user scrolls.
 */
@HiltViewModel
class TelemedicineViewModel @Inject constructor(
    repository: SecureMedRepository
) : ViewModel() {

    val sessionsPagingFlow = Pager(
        config = PagingConfig(pageSize = 20, enablePlaceholders = false),
        pagingSourceFactory = { repository.getTelemedicinePagingSource() }
    ).flow.cachedIn(viewModelScope)
}
