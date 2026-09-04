# SecureMed Development Plan

## Goal
Fix problems and security issues identified across the SecureMed healthcare platform (Django backend + React frontend + Kotlin Android). The plan is ordered by risk and grouped into themes; each item cites concrete files/lines.

## Constraints & Context
- **Architecture**: Single-service production (Django serves API + SPA via WhiteNoise). Dev uses Vite proxy to localhost:8000. AI is a server-side proxy (`/ai/*`) to a separate microservice.
- **Security**: 6 doctor-specified requirements (visibility conditions, permissions, encrypted tokens, biometric login, DB firewall/WAF, encryption). Basin-linked modules with type-based activation.
- **Test baseline**: Claimed 196 backend tests passing (docs/TEST_RESULTS.md), 0 frontend tests, minimal Android unit tests (2-3 files).
- **Environment**: Windows dev, but scripts assume Linux/macOS (bash, venv/bin). Production targets Render/Neon.

---

## 1. Critical Security Issues

### 1.1 Cache poisoning via user-agnostic `cache_page` on ChannelViewSet.list
**File**: `backend/apps/channels/views.py:67-70`
- `@cache_page(60 * 5)` + `@vary_on_headers("Authorization")` caches the channel list response keyed only by the `Authorization` header value. Two different users with the **same** token prefix (or an admin sharing a header) can receive another user's channel data.
- **Fix**: Remove `cache_page` from `list`. Replace with per-user DRF cache or `django-redis` cache with a user-scoped key. The response contains per-user visibility-scoped data, so it must **never** be shared.

### 1.2 SessionSecurityMiddleware is a no-op with JWT auth
**File**: `backend/apps/security/middleware.py:308-350`, `backend/apps/security/session_security.py:46-57`
- `SessionManager.register_session` stores sessions in cache keyed by `active_sessions:{user.id}`. But with JWT auth (no Django session middleware active for the session key), `request.session.session_key` is empty/null, so sessions are never actually tracked. `SessionSecurityMiddleware.__call__` then always sees an empty `sessions` list and skips the fingerprint check (`if sessions and not valid`).
- **Fix**: In `register_session`, store the JWT's `jti` claim or a generated session ID from the token. In `force_logout_user`, rotate the user's JWT signing key version or add the user to a token denylist cache so existing JWTs become invalid.

### 1.3 `dev_settings.py` double-sets EMAIL_BACKEND
**File**: `backend/config/dev_settings.py:97-102`
- Inside the `MOCK_SERVICES` block, line 97 sets `EMAIL_BACKEND` to `console`. Then line 102 unconditionally overrides it to `filebased`.
- **Fix**: Move the `EMAIL_BACKEND` override inside an `else` clause or remove the console one.

### 1.4 `django_ratelimit` in requirements.txt but removed from settings
**File**: `backend/requirements.txt:9`, `backend/config/dev_settings.py:54`, `backend/config/settings.py:371-372`
- Requirements still list `django-ratelimit==4.1.0`, but it's stripped from `INSTALLED_APPS` in dev_settings and commented out in settings. It's never used in production settings either (the comment says "removed" but the package is still installed). This causes a system-check `E003` warning in production when `django-ratelimit` app is not registered but `locmem` cache is used.
- **Fix**: Remove `django-ratelimit` from requirements.txt entirely.

### 1.5 `lock_account` doesn't persist `failed_login_attempts`
**File**: `backend/apps/accounts/models.py:135-136`
- After incrementing `failed_login_attempts` elsewhere, `lock_account` only saves `locked_until`. The `failed_login_attempts` counter is not saved in `lock_account`, so on restart the counter resets. More critically, the login view never calls `lock_account` after incrementing `failed_login_attempts`.
- **Fix**: Ensure `lock_account` saves `failed_login_attempts`, and the login view calls it after N failures.

### 1.6 WAF header scanning includes `HTTP_X_FORWARDED_FOR`
**File**: `backend/apps/security/middleware.py:167`
- `suspicious_headers` includes `HTTP_X_FORWARDED_FOR`. The WAF scans this header against all patterns. Proxy/load-balancer `X-Forwarded-For` values often contain IPs like `127.0.0.1` which match the `SSRF` pattern `http://127\.0\.0\.1` — but actually, X-Forwarded-For is just an IP, not a URL, so it won't match SSRF patterns. However, if a client sends a crafted forwarded value, it could trigger false positives.
- **Fix**: Remove `HTTP_X_FORWARDED_FOR` from `suspicious_headers` (it's already used for IP extraction; scanning it is both redundant and risky).

### 1.7 Reports audit event type is wrong
**File**: `backend/apps/reports/views.py:65`
- `BaseReportView._audited_response` logs `event_type='VULN_SCAN_EXECUTED'` for **all** report downloads (channel PDF, audit Excel, monthly report, etc.).
- **Fix**: Add a `REPORT_GENERATED` or `DATA_EXPORT` event type (already exists in `AuditLog.EventType` at model line 70 and 79) and use it. Pass `report_kind` as a detail.

### 1.8 Password reset token is not explicitly invalidated after use
**File**: `backend/apps/accounts/views.py:791-828`
- `PasswordResetConfirmView` relies on `default_token_generator.check_token()` which is inherently single-use (tied to password hash), but it doesn't explicitly invalidate or blacklist the token. A window exists between password change and next check.
- **Fix**: Generate a custom one-time token, store used tokens in cache/DB, or explicitly invalidate by clearing `mfa_secret` after use. At minimum, document that `check_token` self-invalidates.

---

## 2. Testing Gaps

### 2.1 Test count discrepancy
**Files**: `README.md:7`, `README.md:21`, `docs/TEST_RESULTS.md:4-7`
- README badge says "Tests 96 passed". README line 7 says "96 passed". But `docs/TEST_RESULTS.md:4` says "Total Tests: 196". The test files collectively contain 196 test functions.
- **Fix**: Reconcile all documentation. The correct number is 196 (per docs/TEST_RESULTS.md). Update README badge and line 21 to 196.

### 2.2 No frontend tests
**Files**: `frontend/package.json:11`
- No test runner, no test files. `package.json` has no test script or test dependencies.
- **Fix**: Add Vitest + React Testing Library. Create test setup for auth store, API client, and 2-3 key pages (Login, ProtectedRoute, Dashboard).

### 2.3 Minimal Android tests
**Files**: `android/app/src/test/`
- Only 3 test files: `PatientPagingSourceTest.kt`, `SecurityUtilsTest.kt`, `PatientsViewModelTest.kt`. No tests for API client, repository, authentication flow, or biometric.
- **Fix**: Add tests for `SecureMedApi`, `SecureMedRepository`, `SecurePreferences`, `AuthViewModel`, and `BiometricManager`.

### 2.4 No `test_appointments.py` endpoint tests visible in TEST_RESULTS.md
**File**: `backend/tests/test_appointments.py`
- `test_appointments.py` exists (276 lines) but is not listed in `docs/TEST_RESULTS.md:14-25`. It uses fixtures (`db`) not factories and may not be counted in the pytest run.
- **Fix**: Verify it runs in the pytest suite. Add it to the test results documentation.

---

## 3. Configuration & Deployment Issues

### 3.1 Inconsistent admin credentials across files
**Files**: `backend/config/settings.py:457-458`, `backend/setup.sh:185`, `README.md:50-52`, `backend/.env.example:59`
- `settings.py`: `ChangeMe@2026!`
- `setup.sh`: `SecureMed@2026!`
- `README.md`: `Admin@2026!`
- `.env.example`: `SecureMed@2026!`
- **Fix**: Standardize on `SecureMed@2026!` everywhere. Document this in `.env.example` only.

### 3.2 Android release uses debug signing
**File**: `android/app/build.gradle.kts:37`
- `signingConfig = signingConfigs.getByName("debug")` in the release build type. This means release APKs are signed with the debug key — insecure and will conflict with any production key.
- **Fix**: Create a proper release signing config, or at minimum document that release builds should use a keystore. For demo purposes, add a comment explaining the risk.

### 3.3 `security-crypto` is alpha
**File**: `android/app/build.gradle.kts:105`
- Uses `androidx.security:security-crypto:1.1.0-alpha06` (alpha). Production apps should use the stable `1.1.0` release.
- **Fix**: Upgrade to `1.1.0`.

### 3.4 ENCRYPTION_KEY default is a static string in production
**File**: `backend/config/settings.py:342-345`
- Default ENCRYPTION_KEY is a hardcoded 32-byte string. In production without the env var, all deployments use the same key.
- **Fix**: Remove the default; raise an error if not set in production (`if not DEBUG and not ENCRYPTION_KEY: raise ImproperlyConfigured`).

### 3.5 Frontend API base path inconsistency
**File**: `frontend/src/api/client.ts:5`
- `API_BASE_URL = '/api/v1'` and `baseURL: '/api/v1'`. The axios instance uses a relative base. The refresh endpoint calls `${API_BASE_URL}/auth/refresh/` → `/api/v1/auth/refresh/`. This is correct but the `withCredentials: true` is unnecessary for JWT bearer auth and could cause confusion with CSRF.
- **Fix**: Remove `withCredentials: true` since auth is via Bearer token, not cookies. Or if cookies are used, ensure CSRF is properly handled.

### 3.6 Vite proxy `/ai` rewrite strips `/ai` prefix but proxy target is the wrong service
**File**: `frontend/vite.config.ts:22-26`
- In dev, `/ai` is proxied to `http://localhost:8100` with a rewrite that strips `/ai`. The backend serves `/ai/` at port 8000 (via `config/urls.py:63`). In production, Django handles `/ai/` and proxies to the AI microservice internally.
- The dev proxy is correct for local dev with a standalone AI service, but the rewrite `(path) => path.replace(/^\/ai/, '')` could cause issues if the AI service expects `/ai/ask/` vs `/ask/`.
- **Fix**: Verify with the AI service. The backend `views.py` calls `_ai_url('/ask')` which prepends `AI_SERVICE_URL`, so the AI service expects paths without `/ai` prefix. The rewrite is correct. **No change needed** — verify only.

### 3.7 `MEDIA_ROOT` served via Django in production
**File**: `backend/config/urls.py:93-95`
- In production (non-DEBUG), media files are served by Django via `django.views.static.serve` — this is slow and not secure for production.
- **Fix**: Add a note to serve media via Nginx in the docker-compose full profile. The Nginx config already has `media:/app/backend/media:ro` but doesn't include a location block for `/media/`. Add the Nginx location block.

---

## 4. Code Quality & Performance

### 4.1 GlobalSearch iterates + decrypts all patients in Python
**File**: `backend/apps/accounts/views.py:653`
- `for p in Patient.objects.all()[:500]:` decrypts `full_name` and `national_id` for every patient in the loop. At scale this is O(n) decryption per search with N=500, each decryption doing a PBKDF2 derivation (cached per-process but still expensive).
- **Fix**: Add a DB-level text search on the encrypted fields' hashes, or store a separate searchable hash column. At minimum, use a filtered queryset and limit to 6 results instead of iterating 500.

### 4.2 `from django.db.models import Q` at bottom of patients/views.py
**File**: `backend/apps/patients/views.py:311-312`
- Line 312 has `from django.db.models import Q` at the end of the file, after all classes. This is already imported at the top of the `ai_summary` method (line 162). It's dead code.
- **Fix**: Remove the trailing import.

### 4.3 MedicalFileViewSet lacks `select_related`
**File**: `backend/apps/patients/views_medical_file.py`
- The queryset doesn't `select_related('channel', 'patient', 'uploaded_by')`. Each serialized MedicalFile triggers lazy loads for channel.name, patient.full_name (which does decryption), uploaded_by.full_name.
- **Fix**: Add `select_related` to the queryset.

### 4.4 ChannelViewSet cache key omits user ID
**File**: `backend/apps/channels/views.py:67-70`
- See 1.1. The `@vary_on_headers("Authorization")` doesn't distinguish between users with different tokens — if a reverse proxy strips/normalizes auth headers, different users could get cached responses.
- **Fix**: Per 1.1, remove the decorator.

### 4.5 `audit/middleware.py` logs `DATA_CREATED` for all POSTs
**File**: `backend/apps/audit/middleware.py:27`
- Every POST is logged as `DATA_CREATED`, every PUT/PATCH as `DATA_MODIFIED`, every DELETE as `DATA_DELETED`. This creates a flood of generic audit entries. The `AuditLog.EventType` doesn't have these (it has `DATA_CREATED`, `DATA_MODIFIED`, `DATA_DELETED` at lines 79-81, but the middleware checks `hasattr(AuditLog.EventType, event_type)` which will always be True for these since they're enum members).
- **Fix**: Only log security-relevant POSTs, or refine the logging to be more specific. At minimum, skip low-risk endpoints like `/auth/refresh/`, `/auth/2fa/status/`, `/notifications/unread_count/`.

## 5. Documentation Fixes

### 5.1 README test count
**Files**: `README.md:7`, `README.md:21`, `README.md:74`, `docs/TEST_RESULTS.md:13`
- Update all test count references from 96 → 196.
- Update the test distribution table to include all 12 test files (add `test_appointments.py`, `test_password_reset.py`).

### 5.2 README security table claims
**File**: `README.md:93-97`
- Claims "TLS 1.3" but settings only configure `SECURE_SSL_REDIRECT` and `SECURE_HSTS_SECONDS`. No explicit TLS 1.3 enforcement in Django config (that's a web server / proxy concern).
- **Fix**: Correct to "TLS (HSTS enforced)" or add an Nginx TLS 1.3 config note.

### 5.3 Missing AGENTS.md
No `AGENTS.md` file exists. Create one documenting:
- Backend test command: `cd backend && python -m pytest tests/ -v --cov=apps`
- Frontend build: `cd frontend && npm run build`
- Lint: `cd frontend && npm run lint`

---

## 6. Implementation Order

| Priority | Item | Files | Est. Impact |
|----------|------|-------|-------------|
| P0 | Remove user-agnostic cache from ChannelViewSet.list | channels/views.py | Security (data leak) |
| P0 | Fix SessionSecurityMiddleware no-op with JWT | security/middleware.py, security/session_security.py | Security (session hijack) |
| P0 | Fix report audit event type logging | reports/views.py | Compliance |
| P0 | Fix lock_account persistence | accounts/models.py | Security |
| P1 | Fix dev_settings EMAIL_BACKEND double-set | config/dev_settings.py | Bug |
| P1 | Remove django_ratelimit from requirements | requirements.txt | Config hygiene |
| P1 | Fix admin password inconsistency | settings.py, setup.sh, README.md, .env.example | Bug |
| P1 | Fix test count doc discrepancy | README.md | Docs |
| P1 | Android release signing config | android/app/build.gradle.kts | Security |
| P1 | Remove stale import from patients/views.py | patients/views.py:312 | Code quality |
| P1 | Add select_related to MedicalFileViewSet | views_medical_file.py | Performance |
| P1 | Optimize GlobalSearch patient iteration | accounts/views.py:653 | Performance |
| P2 | Fix audit middleware log flooding | audit/middleware.py | Performance |
| P2 | Add frontend test infrastructure | package.json + test files | Quality |
| P2 | Add Android test coverage | test files | Quality |
| P2 | ENCRYPTION_KEY required in production | settings.py | Security |
| P2 | Add Nginx media serving config | devsecops/docker/nginx.conf | Deployment |

---

## 7. Validation Plan

1. **Security**: Run `bandit -r backend/ -c backend/.bandit.yml` — expect 0 critical issues related to our changes.
2. **Backend tests**: `cd backend && python -m pytest tests/ -v` — expect 196+ passing, 0 failing.
3. **Cache fix**: Verify by logging in as two different users and confirming the channel list is not shared (manual or integration test).
4. **Session security**: Write a test that logs in a user, then accesses with a different device fingerprint, and verifies a 401 SESSION_INVALIDATED response.
5. **Frontend tests**: `cd frontend && npm test` — expect coverage on auth store and API client.
6. **Android tests**: `./gradlew test` — expect tests pass for repository, API, preferences.
7. **Lint**: `cd frontend && npm run lint` and `cd backend && ruff check apps/` (if ruff configured).
