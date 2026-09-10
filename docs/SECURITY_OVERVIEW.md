# SecureMed — Security Overview (نظرة عامة أمنية)

هذه الوثيقة هي نقطة الدخول لأي مراجعة أمنية للمنصة: ما هي الضوابط، أين تُنفَّذ
في الشيفرة، وما الذي يثبت أنها تعمل. التفصيل الكامل موجود في:

- **نموذج التهديد (STRIDE):** `docs/THREAT_MODEL.md`
- **مصفوفة التتبع** (متطلب → شيفرة → اختبار): `docs/SECURITY_TRACEABILITY.md`

---

## 1. نموذج العزل: Basins → Channels → RBAC

العزل ليس دوراً واحداً بل ثلاث طبقات:

1. **الحوض الصحي (Basin)** — وحدة العزل بين المنشآت. `apps.core.mixins.accessible_patients()`
   تقيّد أي queryset مرضى أولًا بنطاق حوض المستخدم ثم بقواعد عضوية القناة.
2. **القناة الطبية (Channel)** — فريق العلاج حول مريض واحد. الوصول للسجلات
   والمرفقات والرسائل يمر عبر `channel.can_view(user)`.
3. **الأدوار (11 دوراً)** — RBAC في `apps.security.permissions_roles`، مع منع
   صريح لدور `PATIENT` من فهرس المرضى (الافتراضي للحسابات الجديدة) ومن
   `AUDITOR` من دليل الموظفين (فصل مهام).

**الإجابة الجاهزة عن سؤال العزل:** مريض في حوض 1 لا يراه طبيب حوض 2 لأن كل
قراءة للمرضى تمر عبر `accessible_patients()` — ويُثبت ذلك باختبار
`test_basins.py::test_hospital_admin_sees_only_own_basin_users` و
`tests/test_security_fixes.py::TestGlobalSearchScoping`.

## 2. المصادقة

| الضابط | التنفيذ |
|---|---|
| كلمات مرور | Argon2 validator، قفل حساب بعد 3 إخفاقات، حظر تصاعدي للجهاز (5 إخفاقات → 30د → 5س → 12س) |
| JWT | RS256 (مفاتيح PEM تحت `backend/certs/`) أو HS256 صراحة؛ تدوير + قائمة حظر بعد التدوير + ربط بالجهاز (`client_fingerprint`) |
| جلسات | سجل جلسات في الكاش، إنهاء جلسة واحدة أو كلها، رفض الاختطاف |
| TOTP 2FA | سر مشفر Fernet، QR يُولَّد في الخادم (لا تمرير السر لطرف خارجي) |
| WebAuthn / البصمة | تحدٍ يُولَّد في الخادم ويُستهلك مرة واحدة؛ تحقق كامل من clientDataJSON وrpIdHash وUV flag وعدّاد التوقيع (`apps/security/crypto.py`) |
| الأجهزة | `ENFORCE_DEVICE_AUTHORIZATION` (حظر الجهاز غير الموثق) أو الوضع التكيفي: جهاز جديد → OTP بالبريد قبل إصدار أي رمز |
| OTP بالبريد | `secrets` + `hmac.compare_digest` |

## 3. حماية البيانات

- **تشفير أعمدة PHI** (الأسماء، الهويات، نصوص السجلات): Fernet عبر
  `apps.security.crypto`، مع بادئة إصدار المفتاح (`v1:`) للسماح بتدوير المفتاح
  مستقبلاً، وسلسلة مفاتيح احتياطية `ENCRYPTION_KEY_FALLBACKS`.
- **تشفير الملفات على القرص** AES-256-GCM (`SMEDF1` header) عبر
  `apps.core.storage.EncryptedFileSystemStorage`.
- **/media/ محمية**: `ProtectedMediaView` — مصادقة إلزامية، تفويض على مستوى
  القناة، تنزيل بدل العرض لكل ما ليس داخل قائمة آمنة، audit لكل قراءة.
- **رفع الملفات**: قائمة امتدادات + فحص magic bytes (`apps.core.uploads`)
  على ملفات المرضى **ومرفقات الاستشارات**، سقف 20MB.
- **سجل التدقيق**: HMAC-SHA256 بمفتاح مستقل عن SECRET_KEY، سلسلة مقفلة
  (Postgres advisory lock)، فحص تلقائي يومي 4 صباحاً (`verify-audit-chain`)
  مع إنذار Telegram، ولا حذف/تعديل من لوحة الإدارة.

## 4. خط DevSecOps

```
Plan ─► Code ─► Build ─► Test ─► Release ─► Deploy ─► Operate
        │        │        │          │          │         │
        │        │        │          │          │         └─ verify_audit_chain (يومي)
        │        │        │          │          │            send_security_digest (يومي)
        │        │        │          │          └─ Trivy (container, يفشل على CRITICAL)
        │        │        │          └─ pytest (427 اختبار) + تغطية
        │        │        └─ Bandit (حاجز) + Semgrep + pip-audit + Safety
        │        └─ Gitleaks (حاجز على الشجرة + مسح تاريخي)
        └─ Security requirements → docs/SECURITY_TRACEABILITY.md
```

- `.github/workflows/security-scan.yml` — SAST + SCA + أسرار (لا `|| true`؛
  كل خطوة إما حاجز أو استشاري موثَّق السبب).
- `.github/workflows/container-scan.yml` — Trivy على الصورة المنشورة فعلاً،
  الحاجز على CRITICAL القابل للإصلاح فقط، ملاحظات موثقة عن CVE-2026-33634
  (سبب عدم استخدام أفعال ثالثة بمراجع متحركة).
- `.github/workflows/tests.yml` — Postgres 15 + Redis 7، تشغيل حزمتي
  `tests/` و`apps/`.
- `devsecops/scripts/security-scan.sh` — الوضع الافتراضي صارم: أداة مفقودة
  تفشل المسح (`SCAN_ALLOW_MISSING=1` للتخطي الصريح محلياً).
- `devsecops/scripts/generate_sbom.sh` — SBOM CycloneDX لـPython وNode.
- حرس الإعدادات في `config/settings.py` يرفض الإقلاع الإنتاجي بمفاتيح افتراضية
  أو كاش لكل عملية (LocMemCache) أو غياب مفتاح HMAC للتدقيق.

## 5. حدود معلومة (Honest limitations)

- certificate pinning في أندرويد يظل هاشاً نائباً حتى إصدار شهادة الإنتاج
  (`docs/ANDROID_DEVELOPMENT_ROADMAP.md` يوثق ذلك).
- التحقق من WebAuthn للتسجيل لا يفحص attestation (مقصود — الثقة تأتي من
  الجلسة المصادَق بها، والتوثيق يشرح السبب).
- لا KMS خارجي؛ التشفير من مفاتيح البيئة. تدوير المفتاح مدعوم عبر
  `ENCRYPTION_KEY_FALLBACKS` + `manage.py rotate_encryption_key`.

## 6. الإبلاغ عن ثغرة

راجع `SECURITY.md` في جذر المستودع.
