package com.securemed.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Block
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.api.ApiErrors
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.data.model.User
import kotlinx.coroutines.launch
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.LoadState
import androidx.paging.cachedIn
import androidx.paging.compose.collectAsLazyPagingItems
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import androidx.hilt.navigation.compose.hiltViewModel

/**
 * Admin-only screen: list, search, activate and deactivate platform users.
 * SUPER_ADMIN and HOSPITAL_ADMIN can toggle accounts; other roles see a
 * friendly "not authorized" state.
 */
private val ADMIN_ROLES = listOf("SUPER_ADMIN", "HOSPITAL_ADMIN")

private fun roleLabel(role: String): String = when (role) {
    "SUPER_ADMIN" -> "مدير النظام"
    "HOSPITAL_ADMIN" -> "مدير مستشفى"
    "DOCTOR" -> "طبيب"
    "NURSE" -> "ممرض/ة"
    "LAB_TECH" -> "فني مختبر"
    "PHARMACIST" -> "صيدلي"
    "AUDITOR" -> "مدقق"
    else -> role
}

private fun roleColor(role: String): Color = when (role) {
    "SUPER_ADMIN" -> Color(0xFFB71C1C)
    "HOSPITAL_ADMIN" -> Color(0xFFE65100)
    "DOCTOR" -> Color(0xFF0D47A1)
    "NURSE" -> Color(0xFF1B5E20)
    "LAB_TECH" -> Color(0xFF4A148C)
    "PHARMACIST" -> Color(0xFF006064)
    "AUDITOR" -> Color(0xFF37474F)
    else -> Color(0xFF616161)
}

@HiltViewModel
class UsersViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    data class State(
        val statusMessage: String? = null
    )

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state

    /**
     * The user list is paged (3-3): the Pager follows the server envelope and
     * loads the next page as the admin scrolls. Local search filters the
     * loaded pages client-side — a server-side `?search=` for this list runs
     * on plaintext columns that do not match the encrypted names.
     */
    val usersPagingFlow = Pager(
        config = PagingConfig(pageSize = 20, enablePlaceholders = false),
        pagingSourceFactory = { repository.getUsersPagingSource() }
    ).flow.cachedIn(viewModelScope)

    private val _refreshRequests = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    val refreshRequests: kotlinx.coroutines.flow.SharedFlow<Unit> = _refreshRequests

    fun toggleUser(user: User) {
        viewModelScope.launch {
            val result = if (user.isActive) repository.deactivateUser(user.id)
            else repository.activateUser(user.id)

            result.fold(
                onSuccess = { msg ->
                    _state.value = _state.value.copy(statusMessage = msg)
                    _refreshRequests.tryEmit(Unit)
                },
                onFailure = {
                    _state.value = _state.value.copy(statusMessage = "تعذر تنفيذ العملية — تحقق من الاتصال")
                }
            )
        }
    }

    fun clearStatusMessage() {
        _state.value = _state.value.copy(statusMessage = null)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun UsersScreen(
    onBack: () -> Unit
) {
    val viewModel: UsersViewModel = hiltViewModel()
    val state by viewModel.state.collectAsState()
    val users = viewModel.usersPagingFlow.collectAsLazyPagingItems()
    val isAdmin = SecurePreferences.userRole in ADMIN_ROLES

    var searchQuery by remember { mutableStateOf("") }
    var pendingUser by remember { mutableStateOf<User?>(null) }

    LaunchedEffect(Unit) {
        viewModel.refreshRequests.collect { users.refresh() }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("إدارة المستخدمين") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "رجوع")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { padding ->
        when {
            !isAdmin -> Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Icon(
                    Icons.Default.Block,
                    null,
                    tint = MaterialTheme.colorScheme.error,
                    modifier = Modifier.size(56.dp)
                )
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    "غير مصرح لك",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    "هذه الشاشة متاحة لمديري النظام والمستشفى فقط",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            users.loadState.refresh is LoadState.Loading && users.itemCount == 0 -> Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                CircularProgressIndicator()
                Spacer(modifier = Modifier.height(12.dp))
                Text("جارٍ تحميل المستخدمين...")
            }

            users.loadState.refresh is LoadState.Error && users.itemCount == 0 -> Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                val error = users.loadState.refresh as LoadState.Error
                Text(
                    ApiErrors.messageFor(error.error, "تعذر تحميل المستخدمين — تحقق من الاتصال"),
                    style = MaterialTheme.typography.bodyLarge
                )
                Spacer(modifier = Modifier.height(12.dp))
                Button(onClick = { users.retry() }) {
                    Text("إعادة المحاولة")
                }
            }

            else -> Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(horizontal = 16.dp)
            ) {
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    modifier = Modifier.fillMaxWidth(),
                    placeholder = { Text("بحث بالاسم أو البريد...") },
                    leadingIcon = { Icon(Icons.Default.Search, null) },
                    singleLine = true,
                    shape = RoundedCornerShape(12.dp)
                )
                Spacer(modifier = Modifier.height(8.dp))

                val filteredCount = (0 until users.itemCount).count { index ->
                    val user = users[index] ?: return@count false
                    searchQuery.isBlank() ||
                        user.fullName.contains(searchQuery, ignoreCase = true) ||
                        user.email.contains(searchQuery, ignoreCase = true)
                }

                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    contentPadding = PaddingValues(bottom = 16.dp)
                ) {
                    items(users.itemCount) { index ->
                        val user = users[index] ?: return@items
                        val matches = searchQuery.isBlank() ||
                            user.fullName.contains(searchQuery, ignoreCase = true) ||
                            user.email.contains(searchQuery, ignoreCase = true)
                        if (matches) {
                            UserCard(
                                user = user,
                                canModify = user.role !in ADMIN_ROLES,
                                onToggle = { pendingUser = user }
                            )
                        }
                    }
                    if (filteredCount == 0) {
                        item {
                            Text(
                                "لا يوجد مستخدمون مطابقون",
                                modifier = Modifier.padding(16.dp),
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                    if (users.loadState.append is LoadState.Loading) {
                        item {
                            Box(
                                modifier = Modifier.fillMaxWidth().padding(16.dp),
                                contentAlignment = Alignment.Center
                            ) { CircularProgressIndicator() }
                        }
                    }
                }
            }
        }
    }

    // Confirm toggle dialog
    pendingUser?.let { user ->
        AlertDialog(
            onDismissRequest = { pendingUser = null },
            title = { Text(if (user.isActive) "إيقاف الحساب" else "تفعيل الحساب") },
            text = {
                Text(
                    if (user.isActive)
                        "سيتم منع ${user.fullName} من الدخول إلى المنصة. يمكن التراجع لاحقاً."
                    else
                        "سيتمكن ${user.fullName} من الدخول إلى المنصة مرة أخرى."
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.toggleUser(user)
                    pendingUser = null
                }) {
                    Text(
                        if (user.isActive) "إيقاف" else "تفعيل",
                        color = if (user.isActive) MaterialTheme.colorScheme.error
                        else MaterialTheme.colorScheme.primary
                    )
                }
            },
            dismissButton = {
                TextButton(onClick = { pendingUser = null }) { Text("إلغاء") }
            }
        )
    }
}

@Composable
private fun UserCard(
    user: User,
    canModify: Boolean,
    onToggle: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(42.dp)
                    .background(roleColor(user.role).copy(alpha = 0.12f), CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = user.fullName.firstOrNull()?.toString() ?: "?",
                    color = roleColor(user.role),
                    fontWeight = FontWeight.Bold
                )
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = user.fullName,
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Box(
                        modifier = Modifier
                            .size(8.dp)
                            .background(
                                if (user.isActive) Color(0xFF2E7D32) else Color(0xFFC62828),
                                CircleShape
                            )
                    )
                }
                Text(
                    text = user.email,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = roleColor(user.role).copy(alpha = 0.1f)
                ) {
                    Text(
                        text = roleLabel(user.role),
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = roleColor(user.role)
                    )
                }
            }
            if (canModify) {
                TextButton(onClick = onToggle) {
                    Icon(
                        if (user.isActive) Icons.Default.Block else Icons.Default.CheckCircle,
                        contentDescription = null,
                        tint = if (user.isActive) MaterialTheme.colorScheme.error
                        else MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(if (user.isActive) "إيقاف" else "تفعيل")
                }
            }
        }
    }
}
