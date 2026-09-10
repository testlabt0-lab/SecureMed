# SecureMed — نموذج التهديد (STRIDE)

النطاق: المنصة كاملة (Backend Django، واجهة React، تطبيق أندرويد، النشر).
المنهجية: Microsoft STRIDE لكل عنصر ثقة في المعمارية، مع الضوابط المرتبطة
بكل تهديد واختبار يثبت الضابط.

## 1. مخطط الثقة

```
[مستخدم] ─HTTPS─► [nginx/Render] ─► [Django ASGI/daphne]
                                        │
        ┌───────────────┬───────────────┼──────────────┬─────────────┐
        ▼               ▼               ▼              ▼             ▼
   [WAF/Throttle]  [DRF + JWT]   [Apps (19)]   [PostgreSQL TLS] [Redis]
                                        │                            │
                                        ▼                            ▼
                                 [/media/ + S3]              [Celery workers]
```

عناصر الثقة: المتصفح/التطبيق (غير موثوق)، حافة الشبكة، طبقة المصادقة،
طبقة التفويض (Basins/Channels)، قاعدة البيانات، الكاش/الوسيط (broker)،
عمليات الخلفية، التخزين.

## 2. STRIDE لكل عنصر

### 2.1 المصادقة (Authentication boundary)

| التهديد | السيناريو | الضابط | إثبات |
|---|---|---|---|
| **S** Spoofing | تخمين كلمة مرور | قفل الحساب + حظر الجهاز التصاعدي + throttling | `test_device_auth_gates.py` |
| **S** | إعادة استخدام refresh token مسروق | تدوير + blacklist + ربط ببصمة الجهاز؛ إعادة التقديم ترجع 401 | `test_security_fixes.py::TestRefreshTokenRotation` |
| **S** | تزييف البصمة/WebAuthn | تحدٍ من الخادم يُستهلك مرة واحدة + تحقق توقيع المفتاح العام + rpIdHash + UV + عدّاد | `test_accounts.py::TestBiometric*` |
| **R** Repudiation | «لم أسجل دخول» | LoginHistory لكل محاولة + AuditLog HMAC | `test_security_fixes.py::TestAuditChainIntegrity` |
| **I** Info disclosure | رسائل خطأ تميز الحسابات الموجودة | ردود متطابقة في تحدي البصمة وإعادة تعيين كلمة المرور | `test_accounts.py`، `test_password_reset.py` |

### 2.2 التفويض (Authorization boundary — الأهم)

| التهديد | السيناريو | الضابط | إثبات |
|---|---|---|---|
| **E** Elevation | دور PATIENT يقرأ مرضى آخرين عبر البحث | `accessible_patients()` قبل أي مسح + منع صريح | `test_security_fixes.py::TestGlobalSearchScoping` |
| **E** | طبيب حوض 2 يقرأ مريض حوض 1 | Basin scoping في كل queryset مرضى | `test_basins.py::test_hospital_admin_sees_only_own_basin_users` |
| **E** | تنزيل ملف مريض من غير عضو القناة | `ProtectedMediaView` + `channel.can_view` | `test_security_fixes.py::TestMediaProtection` |
| **S** | IDOR على سجل/مرفق | تفويض على مستوى الكائن في كل ViewSet + 404 بدل 403 حيث يلزم | `test_phase4_features.py` |
| **I** | دليل API كامل لغير المصادقين | `/api/schema` محجوب خارج DEBUG | `config/urls.py:92` |

### 2.3 المدخلات (Input handling)

| التهديد | السيناريو | الضابط | إثبات |
|---|---|---|---|
| **T** Tampering | SQL injection عبر البحث/الفلاتر | ORM حصرياً + WAF لأنماط SQLi | `test_security.py` |
| **T** | Stored XSS عبر مرفق `evil.html` باسم `.png` | رفض magic bytes غير المطابقة + تنزيل إجباري + nosniff | `apps/core/uploads.py` |
| **T** | رفض الخدمة بملف ضخم | سقف 20MB (رفع) + حد مسح WAF للجسم | `apps/core/uploads.py` |
| **I** | تسميم ملاحظة طبية بتنقية HTML | `SanitizedJSONParser` يلمس النصوص ذات العلامات فقط، كلمات المرور والحقول الشفافة محصنة | `test_input_sanitization.py` |

### 2.4 التخزين (Data at rest)

| التهديد | السيناريو | الضابط | إثبات |
|---|---|---|---|
| **I** | تسريب قاعدة البيانات | تشفير أعمدة PHI (Fernet) + TLS للاتصال | `test_patients.py` |
| **I** | سرقة قرص الملفات | AES-256-GCM لكل ملف (`SMEDF1`) | `apps/core/storage.py` |
| **T** | تعديل سجل التدقيق من صاحب DB | HMAC بمفتاح خارج قاعدة البيانات + سلسلة مقفلة + فحص يومي + إنذار | `test_security_fixes.py`، `test_offsite_and_deactivation.py::test_chain_verification_alerts_on_problems` |
| **R** | حذف سجل من لوحة الإدارة | `has_delete_permission=False` و`has_change_permission=False` | `apps/audit/admin.py` |

### 2.5 سلسلة التوريد والنشر (Build/Deploy)

| التهديد | السيناريو | الضابط | إثبات |
|---|---|---|---|
| **T** | سر في commit | Gitleaks حاجز على الشجرة + مسح تاريخي | `.github/workflows/security-scan.yml` |
| **T** | CVE في التبعيات | pip-audit + Safety + Trivy على الصورة المنشورة؛ حاجز CRITICAL القابل للإصلاح | `.github/workflows/container-scan.yml` |
| **T** | فحص «ينجح» دون فحص | لا `|| true`؛ أداة مفقودة تفشل `security-scan.sh` | `devsecops/scripts/security-scan.sh` |
| **S** | فعل CI متحرك (CVE-2026-33634) | لا أفعال ثالثة بمراجع متحركة في مسار الفحص | تعليق `container-scan.yml` |
| **I** | نشر بمفاتيح افتراضية | حرس إعدادات يرفض الإقلاع | `config/settings.py` (كتلة production guard) |
| **D** DoS | إغراق نقاط API | Rate limit ذرّي (add/incr) + DRF throttling + WAF blocklist | `apps/security/middleware.py` |

### 2.6 الأجهزة والجلسات

| التهديد | السيناريو | الضابط | إثبات |
|---|---|---|---|
| **S** | جهاز غير موثق يدخل | 403 مع طلب توثيق (Telegram) أو تحدي بريدي حسب الوضع | `test_device_auth_gates.py`، `test_adaptive_mfa.py` |
| **S** | انتحال جلسة من جهاز آخر | ربط access token بـ(IP, UA) + فحص بصمة الجلسة | `test_session_security.py` |
| **I** | سر TOTP إلى خدمة QR خارجية | QR يُولَّد في الخادم (data URI) | `SettingsPage.tsx`، `Profile.tsx` |

## 3. المخاطر المقبولة صراحة

1. **attestation غير مفحوص** في تسجيل WebAuthn — مقصود: الثقة من الجلسة
   المصادَق بها، وفحص attestation يضيف محلل CBOR دون قيمة أمنية هنا.
2. **native assertions** تعتمد على أن العميل بنى المفتاح بـ
   `setUserAuthenticationRequired(true)` — لا يمكن فحصه من الخادم؛ موثق في
   `verify_native_assertion()`.
3. **لا KMS** — المفاتيح من البيئة؛ التخفيف: حرس الإعدادات + مسار تدوير.
4. **الوضع الليلي للـSPA** — مخاطر واجهة، خارج نطاق هذا النموذج.

## 4. ما الذي يتغير عند إضافة ميزة جديدة

أي ميزة تلمس بيانات مرضى يجب أن تجيب قبل الدمج:
1. أي queryset تستخدمه؟ — هل يمر عبر `accessible_patients()` أو `can_view()`؟
2. أي ملف ترفعه؟ — هل يستخدم `apps.core.uploads.validate_upload_content`؟
3. أي حدث يولده؟ — أُضيف لـ`AuditLog.EventType`؟
4. أي اختبار يمنع انحدار عزلها؟
