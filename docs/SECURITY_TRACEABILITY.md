# SecureMed — مصفوفة التتبع الأمني (Traceability Matrix)

كل سطر: **متطلب → التنفيذ في الشيفرة → الاختبار الذي يثبته**.
هذه هي الوثيقة التي تحوّل «نقول إننا آمنون» إلى «هذا هو السطر، وهذا الاختبار».

## 1. المصادقة والجلسات

| # | المتطلب | التنفيذ | الاختبار |
|---|---|---|---|
| A1 | تسجيل دخول بريد+كلمة مرور مع قفل الحساب | `apps/accounts/views.py::LoginView`، `LoginSerializer` | `tests/test_accounts.py::TestLoginAPI` |
| A2 | حظر تصاعدي للجهاز بعد 5 إخفاقات | `LoginView` (cache levels + `BlockedDevice.update_or_create`) | `tests/test_device_auth_gates.py` |
| A3 | JWT بتدوير وقائمة حظر | `RefreshTokenView` + `SIMPLE_JWT` في `config/settings.py` | `tests/test_security_fixes.py::TestRefreshTokenRotation` |
| A4 | ربط الرمز بالجهاز (anti-theft) | `apps/security/authentication.py::BoundJWTAuthentication` | `tests/test_session_security.py` |
| A5 | إنهاء جلسة واحدة دون بقية الأجهزة | `apps/security/session_security.py::SessionManager` | `tests/test_session_security.py` |
| A6 | 2FA بـTOTP (إعداد/تفعيل/دخول) | `MFASetupView`، `MFAVerifyView`، `MFALoginView` | `tests/test_phase4_features.py::TestTwoFactor` |
| A7 | OTP بريدي آمن (secrets + compare_digest) | `LoginView` (فرع email)، `MFALoginView` | `apps/accounts/tests/test_adaptive_mfa.py` |
| A8 | WebAuthn كامل (تحدٍ من الخادم، تحقق توقيع، UV، عدّاد) | `apps/security/crypto.py::verify_webauthn_*`، `apps/accounts/serializers.py` | `tests/test_accounts.py::TestBiometric*` |
| A9 | تحدي البصمة لا يكشف وجود الحساب | `BiometricChallengeSerializer` (decoy challenge) | `tests/test_accounts.py` |
| A10 | الوضع التكيفي: جهاز جديد → تحدي بريدي قبل الرموز | `LoginView` (adaptive_challenge) + `MFALoginView` | `apps/accounts/tests/test_adaptive_mfa.py` |
| A11 | حظر الأجهزة غير الموثقة (سياسة الدكتور) | `ENFORCE_DEVICE_AUTHORIZATION` في `LoginView`/`BiometricLoginView`/`MFALoginView` | `tests/test_device_auth_gates.py` |
| A12 | استعادة كلمة مرور بلا تعداد مستخدمين | `PasswordResetRequestView/ConfirmView` | `tests/test_password_reset.py` |

## 2. التفويض والعزل (Basins / Channels / RBAC)

| # | المتطلب | التنفيذ | الاختبار |
|---|---|---|---|
| B1 | عزل الأحواض: مستشفى 1 لا يرى مستشفى 2 | `apps/core/mixins.py::accessible_patients` + `basin_scoped_queryset` | `tests/test_basins.py::test_hospital_admin_sees_only_own_basin_users` |
| B2 | البحث الشامل مقيَّد بالصلاحيات (كان أخطر ثغرة) | `GlobalSearchView` (مسح فوق queryset مقيَّد) | `tests/test_security_fixes.py::TestGlobalSearchScoping`، `tests/test_phase4_features.py::TestGlobalSearch` |
| B3 | دور PATION بلا فهرس مرضى ولا دليل موظفين | `NON_CLINICAL_ROLES` في `apps/core/mixins.py` | `TestGlobalSearchScoping` |
| B4 | وصول القناة يحكم السجلات والمرفقات | `Channel.can_view` + `apps/core/media.py` | `TestMediaProtection` |
| B5 | فصل مهام: AUDITOR قراءة فقط | `apps/security/permissions.py` | `tests/test_phase5_features.py` |
| B6 | إدارة مستخدمين محصورة بأدوار الإدارة | `UserViewSet.get_permissions` + basin scoping | `tests/test_basins.py` |

## 3. حماية البيانات والتشفير

| # | المتطلب | التنفيذ | الاختبار |
|---|---|---|---|
| C1 | تشفير أعمدة PHI (اسم، هوية، سجلات) | `apps/security/crypto.py` (Fernet/MultiFernet) | `tests/test_patients.py` |
| C2 | بادئة إصدار المفتاح `v1:` + تدوير بدون فقدان بيانات | `encrypt_field`/`decrypt_field` + `ENCRYPTION_KEY_FALLBACKS` | `apps/patients` (roundtrip ضمن الحزمة) |
| C3 | تشفير الملفات على القرص AES-256-GCM | `apps/core/storage.py::EncryptedFileSystemStorage` | `tests/test_backups.py` (قراءة عبر storage) |
| C4 | /media/ بمصادقة وتفويض وتدقيق (كانت مفتوحة) | `apps/core/media.py::ProtectedMediaView` | `tests/test_security_fixes.py::TestMediaProtection` |
| C5 | رفع الملفات: امتداد + حجم + magic bytes | `apps/core/uploads.py::validate_upload_content` | الحزمة + `patients` validators |
| C6 | مرفقات الاستشارات كانت بلا فحص — أصبحت مغطاة | `ChatMessageSerializer.validate_attachment` + field validator | `apps/telemedicine` (serializer validation) |
| C7 | TLS إجباري للاتصال بقاعدة البيانات | `config/settings.py` (_DB_SSL_OPTIONS, ssl_require) | حرس الإعدادات |
| C8 | كوكيز آمنة (HttpOnly/Secure/Strict) | `set_refresh_cookie` + إعدادات الجلسة | `apps/security/views.py::_security_features` (قراءة الفعلي) |

## 4. التدقيق والمساءلة

| # | المتطلب | التنفيذ | الاختبار |
|---|---|---|---|
| D1 | سجل تدقيق لكل حدث أمني | `apps/audit/utils.py::log_security_event` | `tests/test_audit.py` |
| D2 | سلسلة HMAC بمفتاح مستقل (tamper-evidence) | `apps/audit/models.py::AuditLog.generate_hash` | `tests/test_security_fixes.py::TestAuditChainIntegrity` |
| D3 | منع تفرّع السلسلة (concurrency) | `pg_advisory_xact_lock` في `AuditLog.save` | `tests/test_audit.py` |
| D4 | كشف التلاعب والإنذار | `verify_audit_chain_task` (Celery beat 4AM) + Telegram | `tests/test_offsite_and_deactivation.py::test_chain_verification_alerts_on_problems` |
| D5 | لا حذف/تعديل للتدقيق من الإدارة | `apps/audit/admin.py` (add/change/delete = False) | مراجعة يدوية (سطر واحد) |
| D6 | IP غير قابل للانتحال في السجلات | `apps/core/net.py::get_client_ip` + `TRUST_X_FORWARDED_FOR` | `tests/test_core_endpoints.py` |
| D7 | لوحة أمان تعرض الإعداد الفعلي لا ادعاءاته | `SecurityDashboardView._security_features` + `_audit_chain_verdict` | `tests/test_phase5_features.py` |
| D8 | وسيط التدقيق يغطي كل API (كان معطلاً بإزاحة) | `apps/audit/middleware.py` | `tests/test_core_endpoints.py::test_audits_counts_only_never_the_payload` |

## 5. خط DevSecOps

| # | المتطلب | التنفيذ | الإثبات |
|---|---|---|---|
| E1 | SAST حاجز (Bandit) | `.github/workflows/security-scan.yml` | خطوة Bandit بلا `|| true` |
| E2 | SCA (pip-audit + Safety) | نفس الملف | تقريران دائمان في artifacts |
| E3 | فحص أسرار (Gitleaks): شجرة حاجز + تاريخ استشاري | job `secrets_scan` | `gitleaks-tree/history.json` |
| E4 | فحص حاوية على الصورة المنشورة، حاجز CRITICAL قابل للإصلاح | `.github/workflows/container-scan.yml` | خطوة `Gate on fixable CRITICAL` |
| E5 | حماية فعل CI من أفعال متحركة | لا أفعال ثالثة في مسار الفحص؛ مرجع CVE-2026-33634 موثق | تعليق رأس الملف |
| E6 | اختبارات على Postgres+Redis حقيقيين | `.github/workflows/tests.yml` | services في الـjob |
| E7 | SBOM لكل بيئة (Python + Node) | `devsecops/scripts/generate_sbom.sh` (CycloneDX) | مخرجات sbom/ |
| E8 | مسح محلي صارم (أداة مفقودة = فشل) | `devsecops/scripts/security-scan.sh` | `require_tool` |
| E9 | رفض إقلاع إنتاجي غير آمن | production guard في `config/settings.py` | رسائل WARNING: ImproperlyConfigured |
| E10 | WAF + Rate limit + Session binding فعّالة ومشتركة | `apps/security/middleware.py` + Redis/DatabaseCache | حرس LocMemCache في الإعدادات |

## 6. الواجهة والعميل

| # | المتطلب | التنفيذ | الإثبات |
|---|---|---|---|
| F1 | CSP بدون `unsafe-inline` للسكربتات | `WAFMiddleware._add_security_headers` | فحص `frontend/dist` (لا inline scripts) |
| F2 | QR للـTOTP من الخادم (لا تسريب سر لطرف خارجي) | `SettingsPage.tsx`/`Profile.tsx` يستخدمان `qr_image` | مراجعة `frontend/src` |
| F3 | WebAuthn client: تحدٍ من الخادم حصراً | `frontend/src/utils/webauthn.ts` | مراجعة + اختبارات الخادم |
| F4 | تنزيل الملفات غير الآمنة إجباري + nosniff | `apps/core/media.py::_serve` | `TestMediaProtection` |

## 7. كيف تحدَّث هذه المصفوفة

أي متطلب جديد أو ضابط جديد يضاف كسطر في القسم المناسب **مع الاختبار في نفس
الcommit**. سطر بلا اختبار أو بلا ملف تنفيذ يعتبر غير منجز — هذا هو المعنى
العملي لـ traceability، وهو نفس المعيار الذي يطبقه المراجع الخارجي.
