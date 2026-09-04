# 📱 Android Development Roadmap — SecureMed

> **Status:** Production-Ready Foundation → Modernization & Hardening
> **Last Updated:** 2026-09-03
> **Target SDK:** 35 | **Min SDK:** 26 | **Language:** Kotlin 1.9+

---

## 1. Executive Summary

The SecureMed Android application already implements a **solid, security-first foundation** using Kotlin + Jetpack Compose + Material 3. This roadmap focuses on elevating it to a **modern, production-grade** app with:

- **Adaptive responsive layouts** (phone / foldable / tablet)
- **Modern Compose patterns** (adaptive scaffolds, state hoisting, derived state)
- **Accessibility & localization** improvements
- **Performance optimizations** (stability, startup time, memory)
- **Security hardening** (Play Integrity, SafetyNet, anti-tampering)
- **Testing coverage** (Compose UI tests, integration tests)
- **Developer experience** (modularization, CI for APK)

---

## 2. Recommended Tech Stack (Current + Future)

| Layer | Current | Recommended / Future |
|-------|---------|---------------------|
| **Language** | Kotlin 1.9.24 | Kotlin 2.0+ (when stable) |
| **UI Toolkit** | Jetpack Compose (BOM 2024.06) | Compose BOM 2024.10+ with Material 3 Adaptive |
| **Architecture** | MVVM + Hilt DI | MVVM + UDF + Hilt + sealed UiState |
| **Networking** | Retrofit + OkHttp + Kotlin Serialization | Same + OkHttp `EventListener` for metrics |
| **Local DB** | Room 2.6.1 + SQLCipher 4.5.4 | Room 2.6.1+ (or 2.7 when stable) |
| **Async** | Coroutines 1.8.1 | Coroutines 1.8.1 + Flow |
| **Image Loading** | Coil 2.6.0 | Coil 2.6.0 + Coil SVG (if needed) |
| **Navigation** | Navigation Compose 2.7.7 | Navigation Compose 2.8.0+ |
| **Paging** | Paging 3.3.0 | Paging 3.3.0 + RemoteMediator (future) |
| **Biometric** | androidx.biometric 1.1.0 | androidx.biometric 1.2.0+ |
| **Security** | EncryptedSharedPreferences + SQLCipher | + Play Integrity API + SafetyNet Attestation |
| **Testing** | JUnit + MockK + Turbine | + Compose Test + Hilt Test |
| **Build Tooling** | AGP 8.5.0 | AGP 8.5+ (or 8.6 when stable) |

---

## 3. Application Architecture

### 3.1 Current Architecture (MVVM)

```
ui/
  screens/          ← Composables + ViewModels (co-located)
  components/       ← Reusable UI (BottomNavBar, StateLayout, PullToRefresh)
  theme/            ← Material 3 theme, typography
data/
  api/              ← Retrofit interface + OkHttp network module
  local/            ← SecurePreferences, LocalCache, MedicationStore
  local/room/       ← Room DB + DAO + Entities (SQLCipher encrypted)
  paging/           ← PatientPagingSource
  model/            ← Kotlin Serialization data models
  SecureMedRepository.kt  ← Single repository (data source abstraction)
auth/               ← BiometricManager (BiometricPrompt wrapper)
di/                 ← Hilt modules (AppModule, DatabaseModule)
navigation/         ← Type-safe Route sealed class
security/           ← SecurityUtils, BiometricHelper
reminders/          ← Alarm + notification scheduling
```

### 3.2 Target Architecture (Clean MVVM + UDF)

**Principles:**
- **Unidirectional Data Flow (UDF):** Events flow down, state flows up.
- **Single source of truth:** Repository owns data; ViewModels expose immutable `StateFlow<UiState>`.
- **One-time events:** Use `Channel<Event>` or `SharedFlow` for navigation, toasts, snackbars — **not** `StateFlow`.
- **Screen contracts:** Each screen defines a sealed `UiState` and a sealed `Event`.

**Proposed package structure:**

```
com.securemed.app/
├── di/                           ← Hilt modules
├── navigation/                   ← Route, NavGraph
├── ui/
│   ├── theme/                    ← Color, Type, Shape, ThemeController
│   ├── components/               ← Reusable atoms (buttons, cards, inputs)
│   ├── screens/                  ← Feature screens
│   │   ├── dashboard/
│   │   │   ├── DashboardScreen.kt
│   │   │   ├── DashboardViewModel.kt
│   │   │   ├── DashboardUiState.kt
│   │   │   ├── DashboardEvent.kt
│   │   │   └── components/       ← Screen-specific composables
│   │   ├── patients/
│   │   ├── channels/
│   │   ├── medications/
│   │   └── auth/
│   └── MainActivity.kt
├── data/
│   ├── api/
│   ├── local/
│   ├── model/
│   ├── paging/
│   └── repository/
├── domain/                       ← (Optional) Use-cases if logic grows
└── util/
```

---

## 4. Modern UI/UX & Material Design Compliance Plan

### 4.1 Material 3 Adaptive Components

Replace static bottom-nav-only navigation with **adaptive navigation**:

- **Phones (< 600dp width):** Keep `NavigationBar` (bottom nav)
- **Foldables / Medium screens (600dp – 840dp):** `NavigationBar` or `NavigationRail`
- **Tablets / Large screens (> 840dp):** `NavigationRail` (side) + `LargeTopAppBar` + `TwoPane` layouts

### 4.2 Responsiveness Strategy

| Breakpoint | Window Size Class | Layout Strategy |
|------------|------------------|-----------------|
| Compact | width < 600dp | Single column, bottom nav |
| Medium | 600dp ≤ width < 840dp | Two columns where appropriate, rail nav |
| Expanded | width ≥ 840dp | Master-detail (list + detail side-by-side), rail nav |

**Implementation:**
- Use `calculateWindowSizeClass(activity)` from `androidx.compose.material3:material3-window-size-class`
- `BoxWithConstraints` for per-screen adaptive decisions
- `Arrangement.spacedBy` + `weight()` for fluid grids
- Avoid hardcoded `Modifier.padding(16.dp)` in favor of a `Spacing` scale

### 4.3 RTL & Internationalization

- Current: RTL hardcoded in `Theme.kt` (`LocalLayoutDirection provides LayoutDirection.Rtl`)
- Target: Use `LayoutDirection.Ltr` dynamically based on locale, not hardcoded
- Extract all Arabic strings to `values-ar/strings.xml`
- Add English fallback in `values/strings.xml`

### 4.4 Accessibility

- Every interactive element needs `contentDescription` or `label`
- Use `Semantics` properties for custom composables
- Ensure 48dp minimum touch target
- Support font scaling (`useTextUnit = false` or scalable `sp`)

---

## 5. Detailed Implementation Plan (Phased)

### Phase 1: Foundation Modernization (Week 1)

| Task | Description | Files |
|------|-------------|-------|
| **Upgrade SDK & BOM** | `compileSdk = 35`, `targetSdk = 35`, Compose BOM 2024.10+ | `build.gradle.kts` |
| **Fix Gradle settings** | `org.gradle.vfs.watch=true`, update JDK path for Windows | `gradle.properties` |
| **Add WindowSizeClass** | Import `material3-window-size-class` and calculate size class in `MainActivity` | `MainActivity.kt`, dependencies |
| **Extract hardcoded strings** | Move Arabic strings from composables to `values-ar/strings.xml` | All `*.kt` screens, `res/values-ar/strings.xml` |
| **Fix certificate pinning** | Replace dummy SHA-256 with actual backend hash or remove for dev | `NetworkModule.kt` |

### Phase 2: Architecture & State Management (Week 2)

| Task | Description | Files |
|------|-------------|-------|
| **Sealed UiState per screen** | Refactor ViewModels to expose `UiState` sealed classes | `*ViewModel.kt` files |
| **One-time events** | Replace `MutableStateFlow<String?>` error messages with `SharedFlow<Event>` | `AuthViewModel.kt`, others |
| **Refactor DashboardScreen** | Extract `StatCard`, `ChannelCard`, `QuickServiceCard` into `components/` | `DashboardScreen.kt`, new files |
| **Add derivedStateOf** | Use for filtered lists, expensive calculations | `PatientsScreen.kt`, `ChannelsScreen.kt` |

### Phase 3: Responsiveness & Adaptive UI (Week 3)

| Task | Description | Files |
|------|-------------|-------|
| **Adaptive scaffold** | Show `NavigationRail` on medium+ screens | `MainActivity.kt`, `BottomNavBar.kt` |
| **Master-detail for tablets** | Split `ChannelList` + `ChannelDetail` on large screens | `ChannelsScreen.kt`, `ChannelDetailScreen.kt` |
| **Fluid grids** | Replace fixed `Row` weight with `LazyVerticalGrid` + `GridCells.Adaptive` | Dashboard stats, Patients grid |
| **BoxWithConstraints** | Use for screens that need column count decisions | `DashboardScreen.kt` |

### Phase 4: Missing Features (Week 4)

| Task | Description | Files |
|------|-------------|-------|
| **ChannelChat screen** | Implement chat/messaging UI for channel members | New: `ChannelChatScreen.kt`, `ChannelChatViewModel.kt` |
| **Forgot password** | Add `ForgotPasswordScreen` with email reset flow | New screen + API endpoint |
| **Terms & Privacy** | Add legal screen with `WebView` or static text | New screen |
| **Onboarding** | First-launch carousel for new users | New screen + `SecurePreferences` flag |
| **Profile photo** | Allow avatar upload via Coil + API | `ProfileScreen.kt` |

### Phase 5: Security Hardening (Week 5)

| Task | Description | Files |
|------|-------------|-------|
| **Play Integrity API** | Detect rooted / emulator / tampered devices | New module + `MainActivity` check |
| **SafetyNet Attestation** | Legacy fallback for API < 30 | New module |
| **Anti-debugging** | Detect debugger + `android:debuggable=false` in release | `SecureMedApp.kt`, `build.gradle.kts` |
| **TLS 1.3 enforcement** | Ensure `ConnectionSpec` uses only TLS 1.3 | `NetworkModule.kt` |
| **ProGuard expansion** | Add rules for Compose, Coil, Kotlinx Serialization | `proguard-rules.pro` |
| **App signing config** | Prepare release signing config (without committing secrets) | `build.gradle.kts` template |

### Phase 6: Testing & Quality (Week 6)

| Task | Description | Files |
|------|-------------|-------|
| **Compose UI tests** | Write tests for Login, Dashboard, Patients screens | `androidTest/` |
| **Hilt test rules** | Add `HiltAndroidRule` for ViewModel tests | `build.gradle.kts`, test files |
| **Screenshot tests** | Add Paparazzi or Robolectric for visual regression | New dependency |
| **CI/CD for APK** | Add GitHub Actions workflow to build + upload debug APK | `.github/workflows/android.yml` |
| **Lint & detekt** | Add `ktlint` + `detekt` for static analysis | New config files |

### Phase 7: Performance & Polish (Week 7)

| Task | Description | Files |
|------|-------------|-------|
| **Baseline Profiles** | Add `Macrobenchmark` + baseline profile for startup | New module |
| **Compose Metrics** | Enable `composeCompilerReports` for skipping analysis | `gradle.properties` |
| **Memory leaks** | Review `remember` / `LaunchedEffect` keys, fix leaks | All screens |
| **Animations** | Add `AnimatedContent` for screen transitions, `Crossfade` for tabs | `MainActivity.kt` |
| **Pull-to-refresh** | Replace custom `PullToRefreshLayout` with `SwipeRefresh` from Accompanist or Material 3 | `PullToRefreshLayout.kt` |

---

## 6. Key Technical Decisions & Rationale

### Why Jetpack Compose?
- **Modern, declarative UI:** Less boilerplate than XML, state-driven.
- **Material 3 native:** Full support for dynamic color, adaptive components.
- **Kotlin-first:** Seamless coroutines, type safety, and null safety.

### Why Hilt over manual DI?
- Compile-time validation
- `@HiltViewModel` eliminates manual `ViewModelProvider.Factory`
- Testability with `@UninstallModules`

### Why SQLCipher?
- Healthcare data (PHI) requires encryption at rest.
- SQLCipher provides AES-256 encrypted Room database.
- Transparent to Room DAOs.

### Why EncryptedSharedPreferences + SQLCipher?
- Defense in depth: tokens in EncryptedSharedPreferences, bulk data in SQLCipher.
- Both use AES-256-GCM / AES-256-SIV.

### Why Retrofit + OkHttp?
- Industry standard, battle-tested.
- Built-in logging interceptor for debug builds.
- `Authenticator` for automatic token refresh on 401.

---

## 7. Responsiveness Checklist

- [ ] All screens use `Modifier.fillMaxSize()` + inner padding from `Scaffold` or `WindowInsets`
- [ ] No fixed `Modifier.width(XXX.dp)` for primary containers
- [ ] `LazyVerticalGrid` with `GridCells.Adaptive(180.dp)` for card grids
- [ ] `NavigationBar` on phones, `NavigationRail` on tablets
- [ ] `LargeTopAppBar` on expanded width
- [ ] `BoxWithConstraints` used where column count must adapt
- [ ] Touch targets ≥ 48dp
- [ ] Font scaling respected (test with system font size 200%)
- [ ] RTL/LTR mirrors correctly (test with Arabic + English locale)

---

## 8. Security Hardening Checklist

- [ ] Play Integrity API integrated
- [ ] SafetyNet Attestation for legacy devices
- [ ] `android:debuggable=false` enforced in release
- [ ] `FLAG_SECURE` on all screens
- [ ] Root detection enhanced (Zygisk, Magisk Hide detection)
- [ ] Certificate pinning with real SHA-256 hashes
- [ ] TLS 1.3 enforced, TLS 1.0/1.1 disabled
- [ ] ProGuard / R8 rules cover all third-party libs
- [ ] API base URL injected via `BuildConfig` (no hardcoded URLs)
- [ ] Sensitive data scrubbed from logs in release
- [ ] Biometric template never logged or cached

---

## 9. Testing Strategy

| Layer | Tool | Coverage Target |
|-------|------|-----------------|
| **Unit** | JUnit 4 + MockK + Turbine | 80%+ of repository & ViewModel logic |
| **Instrumentation** | Espresso + Compose Test | Critical user flows (login → dashboard → patient detail) |
| **Screenshot** | Paparazzi | Visual regression for key screens |
| **Security** | MobSF + manual | OWASP Top 10 checks |
| **Performance** | Macrobenchmark | Startup < 2s on mid-range device |

---

## 10. CI/CD Pipeline

```
.github/workflows/android.yml
├── Trigger: push / pull_request to main
├── Jobs:
│   ├── lint:      ./gradlew lintDebug
│   ├── test:      ./gradlew testDebugUnitTest
│   ├── build:     ./gradlew assembleDebug
│   ├── security:  MobSF scan (or manual step)
│   └── deploy:    Upload APK to GitHub Release (tagged commits only)
```

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Biometric API fragmentation** | Medium | Use `BiometricManager.canAuthenticate()` + graceful fallback |
| **Tablet fragmentation** | Low | Test on 7", 10", foldable emulators |
| **Backend API changes** | High | Use versioned API (`/api/v1/`), integration tests |
| **SQLCipher migration** | Medium | Test DB migration path before enabling encryption |
| **Network security config** | Medium | Clear cleartext policy per build type |

---

## 12. Success Metrics

| Metric | Target |
|--------|--------|
| **Cold start** | < 2 seconds on emulator, < 3s on mid-range device |
| **APK size** | < 25 MB (release, minified) |
| **Test coverage** | 80%+ for repository & ViewModel |
| **Lint errors** | 0 critical / high |
| **Security score** | Pass MobSF OWASP Mobile Top 10 |
| **Accessibility** | Pass Google Accessibility Scanner |

---

*Document generated by Kilo Engineering Agent — SecureMed Android Project 2026.*
