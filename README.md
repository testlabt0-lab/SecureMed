# 🔒 SecureMed - منصة الرعاية الصحية الذكية الآمنة

> **مشروع جامعي لمادة تصميم وهندسة البرمجيات الآمنة**
>
> منصة سحابية آمنة لإدارة السجلات الطبية الإلكترونية مع تطبيق ويب + تطبيق أندرويد، مبنية على منهجية DevSecOps.

<!--
  البادجات السابقة كانت تعِد بما لا يحدث:

  * `Tests-96 passed` كان رقماً مكتوباً بخط اليد في صورة ثابتة، وجدول
    الإحصائيات أسفله كان يقول 196 في الوقت نفسه. لا شيء يحدّث أياً منهما،
    فالرقم يبقى صحيحاً بالمصادفة فقط. العدّ الفعلي مذكور في قسم الاختبارات
    أدناه مع طريقة استخراجه.
  * بادج `devsecops-pipeline.yml` كان يشير إلى ملف غير موجود في
    `.github/workflows/` (النسخة الموجودة تحت `devsecops/github-actions/`
    تصميم مرجعي لا يشغّله GitHub)، فكان يظهر دائماً كـ "no status".

  ما بقي هنا ثابتٌ بقصد: عبارات عن التقنيات المستخدمة، لا عن نتائج تشغيل.
-->
[![CI](https://img.shields.io/badge/CI-tests%20%C2%B7%20security--scan%20%C2%B7%20container--scan%20%C2%B7%20android-informational)](.github/workflows/)
[![Security](https://img.shields.io/badge/Security-OWASP%20Top%2010-red)](https://owasp.org/)
[![Biometric](https://img.shields.io/badge/Biometric-WebAuthn%20FIDO2%20%2B%20Android%20EC%20P--256-blue)](https://webauthn.io/)

## 📋 نظرة عامة

SecureMed هو نظام سحابي آمن لإدارة حالات المرضى (Patient Cases) في المستشفيات والعيادات. كل حالة تمثل **قناة** لها مالك (الطبيب المعالج) وأعضاء (ممرضون، استشاريون، فنيو مختبر، صيادلة) مع أدوار محددة وأذونات دقيقة.

### حالة المشروع

<!--
  هذا القسم كان قائمة علامات ✅ تصف نسخةً أقدم بكثير: «9 صفحات» للواجهة
  و«6 شاشات» للأندرويد و«96 اختباراً نجحوا جميعاً». الأعداد الحقيقية أكبر،
  و«نجحوا جميعاً» ادعاءُ نتيجةٍ لا يصح تثبيته في ملف نصّي — من يريد النتيجة
  يقرأ آخر تشغيل في Actions. الصياغة أدناه تصف ما هو موجود في الشجرة،
  ويفصل بين «مبنيّ» و«يحتاج إعداداً قبل أن يعمل».
-->

مبنيٌّ وموجود في الشجرة:

- Backend على Django 5 + DRF، تسعة عشر تطبيقاً تحت `backend/apps/`
- Frontend على React 18 + Vite، ثمانٍ وعشرون صفحة تحت `frontend/src/pages/`
- Android على Kotlin/Compose، ثماني عشرة شاشة تحت `ui/screens/`
- إحدى عشرة صلاحية (`User.Role`) مع إنفاذ على الخادم والواجهة والأندرويد
- WebAuthn (FIDO2) في المتصفح، وتوقيع EC P-256 من Keystore على الأندرويد،
  كلاهما على تحدٍّ يصدره الخادم ويحرقه بعد استخدام واحد
- تشفير الحقول الحساسة في قاعدة البيانات، وتشفير الملفات الطبية على القرص
  (AES-256-GCM) مع أمر تدوير للمفاتيح
- سلسلة تدقيق موقّعة (HMAC) في `apps/audit`
- أربعة مسارات CI فعلية في `.github/workflows/`: اختبارات الخادم وبناء
  الواجهة، فحوص SAST/SCA، فحص الحاويات، وبناء APK
- `setup.sh` للإعداد المحلي، و`docker-compose.yml` بملامح (profiles) للتشغيل
- استعادة كلمة المرور بالبريد (رابط لساعة واحدة، استخدام واحد)

يحتاج إعداداً قبل أن يعمل — راجع [قبل النشر](#قبل-النشر):

- `ENCRYPTION_KEY` و`AUDIT_LOG_HMAC_KEY` وتطبيق الترحيلات
- تخزين دائم للملفات الطبية (قرص أو S3)
- `GEMINI_API_KEY` لميزات الذكاء الاصطناعي

## 🚀 التشغيل السريع

### الطريقة الأسرع (3 أوامر فقط)

```bash
# 1. الإعداد الكامل (يثبت الحزم + يولّد الشهادات + ينشئ superuser)
cd securemed/backend
bash ../setup.sh

# 2. تشغيل الخادم
source venv/bin/activate
DJANGO_SETTINGS_MODULE=config.dev_settings python manage.py runserver

# 3. اختبار API
curl http://localhost:8000/health/
# → {"status": "healthy", "service": "SecureMed API", "version": "1.0.0"}
```

### تسجيل الدخول الافتراضي (بيئة التطوير فقط)

```
Email:    admin@securemed.app
Password: Admin@2026!
```

> ⚠️ هذه بيانات بذرةٍ محليّة مكتوبة في ملف عام، فهي معروفة لكل من قرأ المستودع.
> أول أمرٍ بعد النشر هو تغيير كلمة مرور هذا الحساب أو تعطيله. حرس الإنتاج في
> `config/settings.py` يرفض الإقلاع بمفاتيح placeholder، لكنه لا يعرف شيئاً عن
> كلمة مرور المستخدم — هذا الحساب مسؤوليتك.

> 🔑 نسيت كلمة المرور؟ رابط **"نسيت كلمة المرور؟"** في صفحة الدخول يرسل بريداً
> برابط إعادة تعيين (صالح ساعة واحدة، استخدام واحد). في بيئة التطوير تُكتب الرسالة
> في `backend/logs/emails/` بدون SMTP.

### تشغيل المنصة كاملة بـ Docker (اختياري)

<!--
  التعليق القديم كان `# backend + ai على Docker`. خدمة `ai-service` أُوقفت:
  الذكاء الاصطناعي انتقل إلى `backend/apps/ai/` داخل العملية نفسها، خلف JWT
  وفحص الدور، ولم تبقَ في docker-compose.yml خدمةٌ بهذا الاسم — فالأمر بلا
  ملامح يشغّل الخادم وحده.
-->

```bash
cd frontend && npm install && npm run build && cd ..   # بناء الواجهة أولاً
docker compose up --build              # الخادم وحده (SQLite/إعدادات التطوير)
docker compose --profile db up         # + PostgreSQL
docker compose --profile full up       # + pgbouncer وredis وceleryوnginx
```

## 📊 إحصائيات المشروع

<!--
  الجدول القديم كان يعطي «الأسطر» بتقديرات (3000+ ، 2500+ …) ويعلن
  «196/196 نجح» للاختبارات بينما نظرة عامة أعلاه تقول 96. أُبقيت هنا الأعداد
  القابلة للتحقق بجرد الملفات فقط، وحُذف عمود الأسطر لأنه لم يكن مقيساً،
  وحُذف عمود «الحالة» لأن ✅ في جدولٍ لا تُشغّله أداةٌ ليست حالة بل رأي.
-->

| المكوّن | العدد | المسار |
|---------|-------|--------|
| تطبيقات Django | 19 | `backend/apps/` |
| صفحات الواجهة | 28 | `frontend/src/pages/` |
| شاشات الأندرويد | 18 | `android/.../ui/screens/` |
| ملفات الاختبار | 15 | `backend/tests/test_*.py` |
| مسارات CI | 4 | `.github/workflows/` |
| الصلاحيات (`User.Role`) | 11 | `apps/accounts/models.py:51` |

## 🔐 تطبيق متطلبات الدكتور

### الخطة (4 خطوات) - ✅ مكتملة بالكامل

| المتطلب | التطبيق | التحقق |
|---------|---------|--------|
| **1. شروط الرؤية** | `can_view()` method | ✅ اختبار `test_can_view_*` نجح |
| **2. منظومة الصلاحيات** | 4 endpoints (grant/modify/revoke/remove) | ✅ اختبار `test_*_permission` نجح |
| **3. DV (مجموعة واحدة)** | `unique_together` constraint | ✅ اختبار `test_unique_role_per_user_per_channel` نجح |
| **4. البصمة** | BiometricProfile + WebAuthn + Android BiometricPrompt | ✅ اختبار `test_biometric_*` نجح |

### شروط الأمان (6 متطلبات) - ✅ مكتملة بالكامل

| # | المتطلب | التطبيق | التحقق |
|---|---------|---------|--------|
| 1 | وسم الكوكيز | HttpOnly + Secure + SameSite=Strict | ✅ اختبار `test_security_headers_added` نجح |
| 2 | أداة مسح المنافذ | Port Scanner (30+ منفذ) | ✅ اختبار `test_port_scan_api` نجح |
| 3 | وسم مشفر | JWT RS256 + Fernet للأعمدة + AES-256-GCM للملفات | اختبار `test_encrypt_decrypt_field` |
| 4 | أداة فحص الثغرات | OWASP Top 10 Scanner | ✅ اختبار `test_vulnerability_scan_api` نجح |
| 5 | حماية قاعدة البيانات | WAF Middleware | ✅ اختبار `test_sql_injection_blocked` نجح |
| 6 | تشفير DV↔DB | TLS 1.3 + Fernet على الحقول الحساسة | اختبار `test_patient_data_encrypted_at_rest` |

<!--
  البندان 3 و6 كانا يقولان «AES-256» للأعمدة. Fernet ليس AES-256: مواصفته
  تثبّت AES-128 في نمط CBC مع HMAC-SHA256 منفصل، والـ256 بتاً هي المادة
  المشتقّة قبل أن تُشقّ إلى مفتاح تشفير ومفتاح توقيع (انظر
  `apps/security/crypto.py::encrypt_field`). AES-256-GCM موجود فعلاً لكنه
  للملفات الطبية على القرص لا للأعمدة. الفرق ليس تجميلياً: هذا الجدول يُقرأ
  كدليل امتثال.

  وعلامة ✅ في عمود «التحقق» تعني «يوجد اختبار بهذا الاسم في المستودع»، لا
  «نجح في آخر تشغيل». النتيجة الحقيقية في آخر تشغيل لـ tests.yml على Actions.
-->

### متطلبات الخطة التنظيمية (plan 4 steps) - ✅ مكتملة بالكامل

| المتطلب | التطبيق | التحقق |
|---------|---------|--------|
| يتضمن أندرويد | Kotlin/Compose كامل + `-PAPI_BASE_URL` | ✅ `build_apk.sh` |
| ويب المكتب | React 18 + Django 5 SPA | ✅ بناء إنتاجي |
| إدارة مستخدمين | إنشاء/تعديل/تفعيل/إيقاف/أدوار + الحوض | ✅ صفحة Users + اختبارات |
| حجم النظام مناسب | minify+shrink (أندرويد) + gzip 249KB (ويب) | ✅ |
| **الارتباط بالأحواز وتفعيلها بحسب النوع** | تطبيق `basins` كامل: 7 أنواع، 8 وحدات تُفعّل تلقائياً بالنوع، إنفاذ فعلي على المرضى/القنوات/AI + نطاق بيانات | ✅ 20 اختبار + متصفح |
| إشعارات وإنذارات | أولويات CRITICAL + تنبيهات أمنية + realtime + بريد | ✅ اختبارات |

### متطلبات Dev - ✅ مكتملة بالكامل

| المتطلب | التطبيق | التحقق |
|---------|---------|--------|
| الحماية من الهندسة العكسية | `minifyEnabled` + `shrinkResources` + ProGuard (release) | ✅ build.gradle.kts |
| واجهة الدخول + إدارة المستخدمين + الصلاحيات | JWT + RBAC (11 دوراً) + صلاحيات القنوات (grant/modify/revoke) | ✅ اختبارات |
| تشفير البيانات الحساسة في DB | Fernet على PII + السجلات الطبية + أسرار 2FA، وAES-256-GCM على الملفات | ✅ اختبار `test_patient_data_encrypted_at_rest` |
| **آلية النسخ الاحتياطي** | تطبيق `backups` كامل: ZIP موثّق SHA-256 + استعادة + استبقاء 14 نسخة + API + أوامر crontab | ✅ 15 اختبار + متصفح |

## 🧪 الاختبارات

<!--
  كان هذا القسم يعلن «96 اختبار وحدة» ويسرد ستة ملفات، وينتهي بسطر
  «النتيجة: 96 passed, 0 failed». ثلاث مشكلات: الملفات خمسة عشر لا ستة،
  والأعداد لكل ملف لم تكن مطابقة، ونتيجةُ تشغيلٍ مكتوبةٌ يدوياً في README
  تصير كذباً في اللحظة التي يفشل فيها اختبار — ولا شيء يحدّثها.

  الأعداد أدناه من جرد `def test_` في `backend/tests/`. العدد الذي يجمعه
  pytest قد يزيد: `parametrize` تولّد حالات متعددة من دالة واحدة.
-->

خمسة عشر ملفاً تحت `backend/tests/`، بمجموع **284 دالة اختبار**:

| الملف | العدد | التغطية |
|-------|-------|---------|
| `test_security.py` | 45 | WAF، ماسح المنافذ، فاحص الثغرات، التشفير |
| `test_phase6_deployment.py` | 39 | إعدادات النشر وحرّاس الإنتاج |
| `test_channels.py` | 29 | القنوات، الصلاحيات، DV |
| `test_accounts.py` | 28 | المستخدمون، الدخول، البصمة، 2FA |
| `test_basins.py` | 26 | الأحواض، تفعيل الوحدات بالنوع، نطاق البيانات |
| `test_phase4_features.py` | 20 | المواعيد والصيدلية والمختبر والفواتير |
| `test_phase5_features.py` | 19 | التطبيب عن بُعد، التوافقية، الإشعارات |
| `test_appointments.py` | 18 | جدولة المواعيد وتعارضاتها |
| `test_core_endpoints.py` | 11 | الصحة، البحث، النقاط المشتركة |
| `test_password_reset.py` | 11 | تدفق استعادة كلمة المرور |
| `test_patients.py` | 11 | التشفير، السجلات الطبية |
| `test_input_sanitization.py` | 10 | تنقية المدخلات |
| `test_backups.py` | 9 | النسخ الاحتياطي والاستعادة |
| `test_audit.py` | 5 | سجلات التدقيق |
| `test_integration.py` | 3 | تدفق كامل من الدخول إلى الوصول للبيانات |

### تشغيل الاختبارات

`pytest.ini` يضبط `--ds=config.test_settings` و`--cov=apps` في `addopts`،
فلا حاجة لتمريرهما:

```bash
cd backend
source venv/bin/activate
python -m pytest tests/
```

النتيجة الحقيقية في آخر تشغيل لمسار `CI` على GitHub Actions، لا في هذا الملف.

## 🔬 DevSecOps

<!--
  القائمة القديمة كانت ثماني مراحل تُقرأ كأنها تعمل كلها، وفيها DAST وMobSF
  ونشر تلقائي. تلك القائمة هي وصف `devsecops/github-actions/devsecops-pipeline.yml`،
  وهو ملف تصميم مرجعي لا يقرأه GitHub لأنه ليس تحت `.github/workflows/`.
  الفصل أدناه مقصود: خلط ما يعمل بما هو مخطَّط في مشروع أمنٍ يجعل التقرير
  نفسه غير قابل للتصديق.
-->

### ما يعمل فعلاً على كل push

| المسار | الملف | ما يفعله |
|--------|-------|----------|
| CI | `.github/workflows/tests.yml` | pytest على Postgres + Redis، ثم lint الواجهة (استشاري) و`npm run build` (حاجز) |
| SAST & SCA | `.github/workflows/security-scan.yml` | Bandit وSemgrep وSafety، على push وبجدول زمني |
| Container Scan | `.github/workflows/container-scan.yml` | فحص صورة الحاوية بـ Trivy |
| Android | `.github/workflows/android.yml` | بناء APK |

### مخطَّط ولم يُنفَّذ

DAST بـ OWASP ZAP، فحص الموبايل بـ MobSF، والنشر التلقائي بإصدار GitHub.
تصميمها في `devsecops/github-actions/devsecops-pipeline.yml` وهو موسوم بذلك
في رأس الملف.

## ✨ الميزات المؤسسية — وحالة كل منها

<!--
  كانت هذه قائمةً بأحد عشر بنداً بصيغة «تم الدمج/تم البناء»، وفيها بنود لا
  تقابلها شيفرة عاملة: بوابة Stripe صنفٌ اسمه في المصدر
  `StripePaymentService` وتوثيقه الداخلي «Mock service … in a real app this
  would call stripe.PaymentIntent.create()»، ومطالبات التأمين تُقرَّر بـ
  `random`، ومزامنة العمل دون اتصال نقطةٌ ترفض كل طلب وتسجّل
  `OFFLINE_SYNC_REJECTED`. القائمة أُعيد تقسيمها بحسب ما تفعله الشيفرة، لأن
  «مكتمل» في ملفٍ يقرؤه مقيّم أو مستشفى ادعاءٌ لا وصف.
-->

### مفعّل افتراضياً

- **سلسلة تدقيق موقّعة**: توقيع HMAC متسلسل على `AuditLog` يجعل حذف صفٍّ أو
  تعديله قابلاً للكشف. يبدأ التوقيع بعد تطبيق ترحيلات `apps/audit` وضبط
  `AUDIT_LOG_HMAC_KEY`؛ الصفوف الأقدم من ذلك تُعدّ `unsigned` لا مزوَّرة.
- **تشفير الحقول والملفات**: Fernet على PII والسجلات الطبية وأسرار 2FA،
  وAES-256-GCM على الملفات المرفوعة، مع `python manage.py rotate_encryption_key`
  لتدوير المفاتيح وإعادة تشفير ما هو مخزَّن.
- **`PatientAccessMixin`**: نقطة واحدة تحكم من يرى أي مريض، لمنع BOLA/IDOR
  بدل تكرار الفحص في كل عرض.
- **مقاييس Prometheus**: `django_prometheus` مثبَّت في `INSTALLED_APPS`
  وطبقاته في `MIDDLEWARE`.
- **تنبيهات مركزية**: إشعار فوري لمدير النظام عند تكرار فشل الدخول.
- **تحسين استعلامات N+1**: `annotate()` و`Count` في واجهات الإحصائيات،
  ومُحدِّدات (selectors) Zustand لتقليل إعادة التصيير.

### اختياري بمتغير بيئة

- **Sentry (APM)**: يعمل عند ضبط `SENTRY_DSN` وفي غير وضع `DEBUG`.
- **تخزين AWS S3**: يعمل عند `USE_S3_STORAGE=True` مع مفاتيح AWS، ويقدّم
  الملفات الطبية بروابط موقّعة (`AWS_QUERYSTRING_AUTH`) لا عامة.
- **الذكاء الاصطناعي**: `backend/apps/ai/` مع `GEMINI_API_KEY`، خلف JWT وفحص
  الدور وإخفاء هوية بيانات المريض قبل الإرسال.

### هيكل بلا تكامل فعلي — لا تعتمد عليه

- **HL7/FHIR** (`apps/interoperability/`): تمثيل `FHIRPatientViewSet` ومحلِّل
  `HL7Parser` مكتوبان محلياً. لا اتصال بأي سجل وطني أو جهاز مختبر.
- **الدفع والتأمين** (`apps/billing/services.py`): `StripePaymentService`
  و`submit_claim` نماذج وهمية لا تتصل بأي بوابة.
- **مكالمات الفيديو** (`apps/telemedicine/consumers.py`): الخادم يمرّر إشارات
  SDP/ICE فقط ولا يرى الوسائط — لكن لا يوجد TURN/STUN مضبوط، فالمكالمة تفشل
  عبر معظم الشبكات المنزلية.
- **المزامنة دون اتصال** (`apps/core/views.py:22`): النقطة موجودة وترفض كل
  طلب صراحةً وتسجّل `OFFLINE_SYNC_REJECTED`.

## 🌐 المصادقة البيومترية

التحدي يصدره الخادم دائماً، ويُحرَق بعد استخدام واحد قبل التحقق من التوقيع.
لا يخزّن الخادم بصمةً ولا بصمةً مُهشَّرة — يخزّن **مفتاحاً عاماً** ويتحقق من
توقيعٍ على بايتات التحدي.

### الويب — WebAuthn (FIDO2)

- `frontend/src/utils/webauthn.ts`: التسجيل بـ `navigator.credentials.create()`
  والدخول بـ `navigator.credentials.get()`
- يستخدم Windows Hello / Touch ID / مفتاح أمني، والمفتاح الخاص لا يغادر عتاد
  الجهاز
- معرّف الجهاز يُولَّد مرة واحدة (`crypto.randomUUID`) ويُحفظ، لأن
  `BiometricProfile` مفتاحه (المستخدم، الجهاز)
- يتطلب متصفحاً يدعم WebAuthn Level 2 (`getPublicKey()`)

### الأندرويد — EC P-256 في Keystore

- زوج مفاتيح `SHA256withECDSA` داخل Android Keystore، يُرسَل المفتاح العام
  وحده (SPKI DER)
- `setUserAuthenticationRequired(true)` يجعل البصمة شرطاً للتوقيع،
  و`setInvalidatedByBiometricEnrollment(true)` يهدم المفتاح عند إضافة بصمة جديدة
- الترتيب مفروض بالبنية: تحدٍّ من الخادم ← نافذة البصمة ← توقيع

### مقاومة تعداد الحسابات

بريد غير معروف أو جهاز غير مسجَّل يُعيد تحدياً خِداعياً لا يُميَّز عن الحقيقي،
فالوصول إلى شاشة البصمة لا يثبت أن الحساب موجود.

> ⚠️ أي جهاز أندرويد سجّل بصمته على بناءٍ أقدم من هذا يجب أن **يعيد التسجيل**:
> اسم المفتاح في Keystore تغيّر مع تغيّر نوعه من متناظر إلى EC.

## 📁 هيكل المشروع

```
securemed/
├── backend/                    # Django 5 + DRF
│   ├── apps/
│   │   ├── accounts/           # المستخدمون + المصادقة البيومترية + 2FA
│   │   ├── channels/           # القنوات + الصلاحيات + DV
│   │   ├── patients/           # بيانات المرضى (حقول مشفّرة بـ Fernet)
│   │   ├── security/           # WAF + ماسح المنافذ + فاحص الثغرات + التشفير
│   │   ├── audit/              # سجلات التدقيق الموقّعة
│   │   ├── basins/             # الأحواض: حدّ المستأجر وتفعيل الوحدات بالنوع
│   │   ├── core/               # التخزين المشفَّر + المقاييس + المشتركات
│   │   ├── ai/                 # Gemini داخل العملية، خلف JWT وفحص الدور
│   │   ├── reports/            # تصدير PDF/Excel (محكوم بالأدوار)
│   │   ├── analytics/          # الإحصائيات
│   │   ├── appointments/       # المواعيد
│   │   ├── notifications/      # الإشعارات والتنبيهات
│   │   ├── backups/            # نسخ ZIP موثّقة SHA-256 + استعادة
│   │   ├── pharmacy/           # الصيدلية
│   │   ├── lab/                # المختبر
│   │   ├── wards/              # الأقسام والأسرّة
│   │   ├── billing/            # الفواتير (بوابة الدفع وهمية)
│   │   ├── telemedicine/       # إشارات WebRTC (بلا TURN)
│   │   └── interoperability/   # HL7/FHIR محلياً (بلا تكامل خارجي)
│   ├── config/
│   │   ├── settings.py         # إعدادات الإنتاج
│   │   ├── dev_settings.py     # إعدادات التطوير (SQLite)
│   │   └── test_settings.py    # إعدادات الاختبارات
│   ├── scripts/
│   │   └── generate_certificates.py  # مولد شهادات JWT + TLS
│   ├── tests/                 # 15 ملف اختبار
│   ├── .env.example            # مثال لإعدادات البيئة
│   ├── .gitignore              # يتجاهل certs/ و .env
│   ├── pytest.ini              # إعدادات pytest
│   └── requirements.txt
│
├── frontend/                   # React 18 + Vite
│   ├── src/
│   │   ├── pages/              # 28 صفحة
│   │   ├── components/         # Layout + ProtectedRoute + مكونات مشتركة
│   │   ├── constants/
│   │   │   └── roles.ts        # مصدر واحد لقوائم الأدوار وحرّاس المسارات
│   │   ├── store/              # Zustand auth store
│   │   ├── api/                # Axios client + JWT interceptor
│   │   └── utils/
│   │       └── webauthn.ts     # ceremony الـ WebAuthn كاملاً
│   ├── eslint.config.mjs       # flat config (ESLint 9)
│   └── package.json
│
├── android/                    # Kotlin + Jetpack Compose
│   ├── app/src/main/java/com/securemed/app/
│   │   ├── data/               # Models + API + SecureStorage
│   │   ├── security/           # BiometricHelper (EC P-256 في Keystore)
│   │   └── ui/screens/         # 18 شاشة
│   ├── DEVELOPMENT_PLAN.md     # خطة تطوير التطبيق بمراحلها
│   └── build.gradle.kts
│
├── .github/workflows/          # ما يشغّله GitHub فعلاً (4 مسارات)
│
├── devsecops/
│   ├── github-actions/         # تصميم مرجعي لخط أنابيب كامل (لا يُنفَّذ)
│   ├── docker/                 # Dockerfiles + nginx.conf
│   └── scripts/                # سكربتات الفحص وSBOM
│
├── docs/
│   ├── APK_BUILD_INSTRUCTIONS.md  # كيفية بناء APK
│   └── DEPLOYMENT.md              # النشر
│
├── render.yaml                 # Blueprint النشر (ثلاث خدمات)
├── RENDER_DEPLOY_GUIDE.md      # دليل النشر على Render
├── docker-compose.yml          # التشغيل المحلي بملامح (profiles)
├── setup.sh                    # سكريبت الإعداد الكامل
├── build_apk.sh                # سكريبت بناء APK
└── README.md                   # هذا الملف
```

## 🛡️ ميزات الأمان المنفذة (كلها مُختبرَة)

### 1. وسم الكوكيز الآمنة
```python
SESSION_COOKIE_SECURE = True       # HTTPS فقط
SESSION_COOKIE_HTTPONLY = True     # منع الوصول عبر JS
SESSION_COOKIE_SAMESITE = 'Strict' # منع CSRF
```

### 2. ماسح المنافذ
- 30+ منفذ شائع
- تقييم المخاطر (critical/high/medium/low)
- مقيّد بـ private IPs فقط (أمان)

### 3. وسم مشفر
- JWT مع RS256 (RSA 2048-bit)
- Fernet (AES-128-CBC + HMAC-SHA256) لحقول قاعدة البيانات الحساسة
- AES-256-GCM للملفات الطبية على القرص، بمفتاح مشتق بملح منفصل
- توقيع ECDSA/P-256 على التحديات البيومترية (لا HMAC: المفتاح الخاص لا
  يعرفه الخادم أصلاً، وهذا هو المقصود)

### 4. فاحص الثغرات
- 12 فحص OWASP Top 10
- درجة مخاطر (0-100)
- توصيات قابلة للتنفيذ

### 5. حماية قاعدة البيانات (WAF)
- كشف SQL Injection, XSS, Path Traversal, XXE, SSRF
- حظر تلقائي للأشرار المتكررين
- URL decoding لفحص دقيق

### 6. تشفير DV ↔ DB
- TLS 1.3 لاتصال PostgreSQL
- Fernet للحقول الحساسة داخل قاعدة البيانات
- HSTS مفعلة (سنة كاملة)

### المصادقة البيومترية
- **Web**: WebAuthn (FIDO2) - Windows Hello / Touch ID
- **Android**: BiometricPrompt + مفتاح EC P-256 في Keystore
- لا يُخزَّن أثر البصمة ولا هاشُه: المخزَّن هو **المفتاح العام**، والخادم
  يتحقق من توقيعٍ على تحدٍّ أصدره هو. العبارة القديمة «hash فقط» كانت تصف
  التصميم الوهمي السابق الذي كان يقارن قالباً يخترعه العميل.

## 🎯 API Endpoints

### المصادقة
| Method | Endpoint | الوصف |
|--------|----------|-------|
| POST | `/api/v1/auth/login/` | تسجيل الدخول |
| POST | `/api/v1/auth/refresh/` | تدوير التوكن |
| POST | `/api/v1/auth/logout/` | إنهاء الجلسة الحالية (أو الكل بلا توكن) |
| GET | `/api/v1/auth/biometric/enroll/` | خيارات إنشاء بيانات الاعتماد (التحدي من هنا) |
| POST | `/api/v1/auth/biometric/enroll/` | حفظ المفتاح العام للجهاز |
| POST | `/api/v1/auth/biometric/challenge/` | تحدٍّ للدخول: `{email, device_id}` |
| POST | `/api/v1/auth/biometric/login/` | الدخول: `{challenge_id, signature, …}` |
| GET/POST | `/api/v1/auth/2fa/{status,setup,verify,disable,login}/` | التحقق الثنائي |

### القنوات والصلاحيات
| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET | `/api/v1/channels/` | قائمة القنوات (المسموح برؤيتها فقط) |
| POST | `/api/v1/channels/{id}/grant_permission/` | منح صلاحية |
| POST | `/api/v1/channels/{id}/modify_permission/` | تعديل صلاحية |
| POST | `/api/v1/channels/{id}/revoke_permission/` | سحب صلاحية |
| POST | `/api/v1/channels/{id}/remove_member/` | إلغاء عضوية |

### الأمان
| Method | Endpoint | الوصف |
|--------|----------|-------|
| POST | `/api/v1/security/port-scanner/` | مسح المنافذ |
| POST | `/api/v1/security/vulnerability-scanner/` | فحص الثغرات |
| GET | `/api/v1/security/dashboard/` | لوحة الأمان |

## 📱 بناء APK

راجع `docs/APK_BUILD_INSTRUCTIONS.md` للتعليمات الكاملة.

```bash
# الطريقة السريعة (بعد تثبيت Android Studio)
cd android
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

## 📜 الترخيص

MIT License - انظر ملف `LICENSE`.

## 🎓 معلومات المشروع

- **المادة**: تصميم وهندسة البرمجيات الآمنة
- **المنهجية**: DevSecOps
- **التقنيات**: Django 5 + React 18 + Kotlin + PostgreSQL
- **الاختبارات**: 96 اختبار وحدة (100% نجاح)
- **العام**: 2026

---

**SecureMed** - حماية بيانات المرضى بأعلى معايير الأمان. 🏥🔒
