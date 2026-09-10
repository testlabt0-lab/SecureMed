# خطة تحويل SecureMed من مشروع متقدم إلى منتج جاهز للإطلاق

> أُعدت في 2026-09-10 بناءً على تحقق مباشر من الشيفرة (ليس من الوثائق)، مع مقارنة تقرير التدقيق `SECUREMED_AUDIT_2026-09-04.md` وسجل التطوير `docs/DEVELOPMENT_LOG.md` بالحالة الفعلية للملفات.

---

## 0. القرارات المحسومة مع المستخدم

| القرار | القيمة |
|---|---|
| بيئة النشر النهائية | **VPS/Docker كامل** (daphne + postgres + redis + celery + coturn + مراقبة) — يُلغى مسار SmarterASP/IIS نهائياً |
| الوحدات "الاسمية" | **كلها تتحول لوظائف حقيقية**: مزامنة دون اتصال، فيديو حقيقي، فوترة ودفع حقيقي، HL7/FHIR |
| بوابة الدفع | تجريد `PaymentGateway` + محوّل **Moyasar** افتراضي (SAR/مدى/Apple Pay، وضع sandbox) + بنية تقبل Stripe لاحقاً (قرار بديل بعد إسكات السؤال) |
| HL7/FHIR | واجهة **FHIR R4 عامة قابلة للربط** (استيراد/تصدير + عميل صادر قابل للتهيئة لأي نظام شريك مستقبلاً) — لا ربط بمورد محدد (NPHIES يتطلب اعتماداً رسمياً خارج نطاق الكود) |

---

## 1. تحليل الوضع الراهن

### 1.1 حجم المشروع (متحقق منه)
19 تطبيق Django · 28 صفحة React · 18+ شاشة أندرويد Compose · ~415 اختباراً خادمياً + 63 اختبار أندرويد · CI حقيقي (`.github/workflows/tests.yml`: خادم على Postgres+Redis، ويب، أندرويد).

### 1.2 ما هو حقيقي ومختبر — لا يُعاد بناؤه
- **المصادقة**: JWT مربوط ببصمة الجهاز + تدوير رمز التحديث وقائمة حظر (`accounts/views.py:393-466`) + 2FA + WebAuthn + بصمة أندرويد EC P-256 بتوقيع تحدٍّ صادر من الخادم + اعتماد أجهزة عبر Telegram.
- **الأمان**: WAF + تحديد معدل + سلسلة تدقيق HMAC متسلسلة (`audit/models.py:289-379`) + تشفير حقول Fernet مع إصدار `v1:` وأمر تدوير (`security/crypto.py:107-131`) + تشفير ملفات AES-256-GCM + `ProtectedMediaView` + فحص magic bytes للرفع (`core/uploads.py`) + محلل JSON منقّى بلا إفساد كلمات المرور (`security/parsers.py`).
- **البحث العام** مُقيَّد بالحوض/القناة (`accounts/views.py:1110-1202`) و**لوحة الأمان** تقرأ الإعداد الفعلي (`security/views.py:153+`).
- **FCM push حقيقي** (HTTP v1، توكنات، تفضيلات: `notifications/push.py`).
- **النسخ الاحتياطي** ZIP موثّق + توصيل Telegram/S3، **تقارير** PDF/Excel عربية، **أحواض** بتفعيل وحدات حسب النوع.

### 1.3 الثغرات المتبقية (مُتحقَّق منها، مرتبة بالخطورة)

**أ. أمن/جلسات (ويب)**
1. التوكنات في `sessionStorage` عبر Zustand persist (`store/authStore.ts:33-52`) — مقروءة بـJS ومعرّضة لXSS.
2. **خلل تدوير رمز التحديث**: الخادم يدوّر ويعيد `payload.refresh` (`accounts/views.py:447-465`) لكن `client.ts:78-86` يقرأ `access` فقط ويعيد تخزين التوكن القديم المحظور → **قسر تسجيل خروج بعد أول تجديد صامت**. كما أن نداء refresh يستخدم axios خاماً بلا ترويسة `X-Device-Fingerprint` بينما الخادم يربط الرمز بها (`views.py:426-435`).
3. مقارنة نصوص عربية حرفية لكشف الحظر (`client.ts:57`, `Login.tsx:64-72`) — تنكسر بأي تغيير صياغة (الخادم: `security/middleware.py:100-124`).
4. إعادة حساب SHA-256 لبصمة الجهاز عند **كل** طلب (`client.ts:24` + `utils/deviceFingerprint.ts`).

**ب. تشغيلية/نشر**
5. تناقض نشر ثلاثي: `web.config` يثبّت Python 3.9 (لا يشغّل Django 5 أصلاً) + `smarterasp-deploy.yml` يرفع الخادم عبر FTP + `render.yaml` بخطة مجانية تعمل بـLocMemCache وInMemory channels (الحراس في `settings.py:991-1005` تحذر من ذلك حرفياً).
6. `docker-compose.yml` طوبولوجيا منفصلة الأصول (SPA على nginx:3000 + API على :8000 → تعقيد CORS/CSRF)، و`backend/Dockerfile` لا يبني الـSPA (فالـcatch-all سيعيد 404)، ولا توجد خدمة **coturn** → كل مكالمات الفيديو تفشل عبر NAT/الجدران.
7. حطام مستودع: `backend_obfuscated/`، `SecureMed-main/` (نسخة كاملة ثانية)، `scratch/`، 5 أرشيفات zip/tar، `test_500*.py`، `_fixes_batch2.py`، `comments_mapping.json` (التعليقات مستعادة أصلاً في الشيفرة)، مخرجات اختبارات في `backend/` (`test_output*.txt`, `accounts_*.txt`, `full_test_results*.txt`, `pip_list.txt`, `dump_serializers.py`, `test_patients.py`, `db.sqlite3.bak-preview`, `.pytest_tmp/`, `htmlcov/`)، بيئتا venv، `frontend/dist` ملتزم في الشجرة، `refactor_zustand.js`.

**ج. أندرويد (متحقق منها)**
8. `MedicationStore.kt` يستخدم `runBlocking` وتُستدعى دواله من Main dispatcher في `MedicationsViewModel` → SQLCipher متزامن على خيط الواجهة (ANR).
9. طابور المزامنة سام: أي 4xx يعاد للأبد (`SyncWorker.kt:54-62`)، والواجهة تُخدع بنجاح مزيف بمعرّف `temp_` (`SecureMedRepository.kt:452-488`)، بلا مفتاح idempotency (تكرار عند الموت بين POST والحذف)، وWork بلا `Unique`.
10. توكن FCM لا يُلغى عند الخروج (`unregisterPushToken` بلا مستدعٍ — `SecureMedRepository.kt:974-979`) → إشعارات سريرية لجهاز مسجّل الخروج.
11. pin-set المنصة في `network_security_config.xml:8` على `securemed-web.onrender.com` بينما مضيف API الفعلي `securemed-production.onrender.com` → الحماية على مستوى النظام لا تسري على الـAPI.
12. `ProfileScreen.kt:118-122` يرسل اسم المستخدم إلى `ui-avatars.com` الخارجي عند كل عرض (تسريب بيانات هوية لطرف ثالث في تطبيق طبي).
13. هويتان للجهاز: `deviceId` ضعيف (`android-<ts>-<rand>`) للتسجيل/الدفع مقابل `installId` القوي للأمان (`SecurePreferences.kt:293-359`).
14. شيفرة ميتة: `getSecurityDashboard` بلا مستدعٍ، `AppointmentEntity` لا تُقرأ ولا تُكتب، `createPatient()` لا يصلها UI، `GlobalErrorHandler` شبه معطّل.

**د. ويب (متحقق منها)**
15. 2FA مكررة ثلاث مرات (Profile/SecuritySettings/SettingsPage) بلا مكوّن مشترك (الـAPI وحّد فقط).
16. لا i18n إطلاقاً + مبدّل لغة زائف بلا onClick (`SettingsPage.tsx:737-740`)، ونصوص ثابتة في JSX.
17. صفر اختبارات ويب (لا Vitest ولا RTL)، `no-explicit-any: off` مع ~257 `any`، و`data: any` في طبقة API كاملة.
18. ميت/زائد: `Analytics.tsx` غير موصول، تبعيات `@radix-ui/*` و`clsx` غير مستخدمة، كتالوج التقارير مكرر يدوياً في `Reports.tsx` رغم وجود `GET /reports/list/`، استيرادات ميتة.
19. نوافذ مودال بلا `role="dialog"`/focus-trap رغم وجود `common/Modal.tsx`.

**هـ. وحدات اسمية (المحرك الأساسي للقسم 3)**
20. **الفوترة**: `StripePaymentService` موك يولّد UUIDs، و`InsuranceService.submit_claim` يقرر بـ`random` (`billing/services.py`) — رغم وجود نماذج `PaymentTransaction` و`InsuranceClaim` جاهزة.
21. **المزامنة دون اتصال**: `OfflineSyncAPIView` ترفض بـ501 (`core/views.py`) — لا نموذج VitalSigns ولا `client_op_id` (`patients/models.py` يحوي Patient/MedicalRecord/MedicalFile فقط).
22. **الفيديو**: الإشارات صحيحة ومصرّح بها (`telemedicine/consumers.py`) لكن بلا TURN/STUN من الخادم (الويب يقرأ `VITE_TURN_*` غير المضبوطة)، وشاشة الأندرويد list-only.
23. **HL7/FHIR**: قراءة فقط، محلل HL7 مكتوب يدوياً، لا استيراد ولا عميل صادر.

---

## 2. خطة الإصلاح (الأخطاء البرمجية والمنطقية)

### P0 — الأمن والجلسات (قبل أي نشر)
1. **تدفق الرموز (ويب)** في `frontend/src/api/client.ts` + `store/authStore.ts`:
   - النداء التجديدي يستخدم نفس نسخة axios المضبوطة (ترويسات البصمة تُرسل).
   - حفظ `response.data.refresh` عند وجوده (إصلاح قسر الخروج) + تحديث الكوكي التي يضبطها الخادم.
   - نقل `refresh` خارج `sessionStorage`: access في الذاكرة فقط، refresh في كوكي HttpOnly يديره الخادم (الخادم يقرأ الكوكي أصلاً في `accounts/views.py:405`) — وحذف persist للرموز من authStore.
2. **أكواد خطأ آلية**: إضافة `"code"` لردود الحظر في `apps/security/middleware.py` (مثل `DEVICE_BLOCKED`, `IP_BLOCKED`, `PENDING_DEVICE`) ومطابقة `code` بدل النص في `client.ts:57` و`Login.tsx` (النص يبقى للعرض).
3. **كاش بصمة الجهاز**: promise مُخزَّنة module-level في `deviceFingerprint.ts`.
4. **أندرويد N8/N9**: تحويل دوال `MedicationStore` إلى suspend + `Dispatchers.IO`، ومراجعة المستدعين في `MedicationsScreen.kt` وال receivers.
5. **أندرويد N10**: استدعاء `unregisterPushToken` في `logout()` و`clearAllForWipe`، وتوحيد هوية الجهاز على `installId` (N13) مع ترحيل صفوف التوكنات القديمة.
6. **أندرويد N11**: تصحيح pin-set في `network_security_config.xml` ليطابق مضيف الإنتاج الفعلي (مع توثيق تاريخ الانتهاء والتجديد).

### P1 — تشغيلي
7. **حذف مسار SmarterASP**: `.github/workflows/smarterasp-deploy.yml` و`backend/web.config` (وسم الإلغاء في README).
8. **توحيد Docker**: كل الخدمات من `Dockerfile` الجذري متعدد المراحل (يبني SPA ويخدمه Django بنفس الأصل)؛ إلغاء `backend/Dockerfile`+`entrypoint.sh` وخدمة frontend المنفصلة أو تحويلها لوكيل TLS فقط؛ TLS عبر nginx بشهادات من مجلد `deploy/certs`؛ إضافة خدمة **coturn** (القسم 3.B)؛ ملف `.env.docker.example` محدَّث بكل المفاتيح (REDISS, FCM, TURN secret, Moyasar, GEMINI).
9. **إصلاح طابور المزامنة الأندرويد**: 4xx → حذف العملية مع حالة خطأ ظاهرة للمستخدم؛ `UniqueWork` للمزامنة؛ إرسال `client_op_id` (UUID مخزَّن مع العملية)؛ إزالة "النجاح المزيف" — الواجهة تعرض "محفوظ محلياً — بانتظار المزامنة".
10. **تنظيف المستودع** (بند 6 أعلاه) + تحديث `.gitignore` (قواعد `*.txt` الكاسحة تستثني requirements) + حذف `frontend/dist` من الشجرة وتبعيات radix/clsx و`Analytics.tsx` والميت (N14).
11. **CI**: مراجعة `security-scan.yml` من `|| true` ورفع SARIF فعلياً؛ إزالة `continue-on-error` من lint بعد جولة تنظيف؛ إضافة job لاختبارات ويب الجديدة (القسم 3.F).

### التحقق
- `pytest tests apps` أخضر، `npm run build` + اختبارات Vitest الجديدة، `gradlew testDebugUnitTest detekt` أخضر.
- تدفّق يدوي: تسجيل دخول → انتظار انتهاء access → تجديد صامت يستمر > 15 دقيقة بلا خروج.

---

## 3. خطة التطوير الوظيفي (الاسمي → حقيقي)

### A. المزامنة دون اتصال (خادم + أندرويد)
- **خادم** `apps/patients`:
  - نموذج `VitalSigns` (patient FK، نوع القياس، القيمة، الوحدة، وقت القياس، مصدر الجهاز) + ترحيل.
  - عمود `client_op_id` (UUID, unique) على `VitalSigns` و`MedicalRecord` للاستنتاج من التكرار.
  - إعادة كتابة `OfflineSyncAPIView` (`core/views.py`) لدفعة حقيقية: تُعيد لكل عملية `{status: created|duplicate|rejected, id, reason}`، بصلاحيات `accessible_patients`، تدقيق، وبدون تسجيل PHI في اللوج.
  - 15+ اختباراً: دفعة مختلطة، تكرار نفس `client_op_id`، عملية لمريض غير مصرّح، سلوك ترتيبي.
- **أندرويد**: توسيع `SyncWorker` (نوع `CREATE_VITAL_SIGN`)، إصلاحات P1-9، مؤشر "بانتظار المزامنة" في PatientDetail.

### B. مكالمات الفيديو الحقيقية (TURN)
- خدمة **coturn** في `docker-compose.yml` (3478/5349 UDP+TCP، relay 49160-49260/udp) مع بيانات REST قصيرة العمر (HMAC secret مشترك).
- نقطة `GET /api/v1/telemedicine/rtc-config/` تصدر `{iceServers}` ببيانات اعتماد موقّعة صالحة ~ساعة، خلف مصادقة القناة نفسها.
- الويب `useWebRTCCall.ts`: جلب الإعدادات من الخادم بدل `VITE_TURN_*` (يبقى fallback للبيئة المحلية).
- **أندرويد**: شاشة استشارة (تفاصيل + دردشة REST الموجودة `telemedicine/messages/`) + شاشة مكالمة 1:1 بمكتبة WebRTC الأصلية معلقة على نفس consumer `ws/video_call/<room>/` مع subprotocol التوكن نفسه. *خطة بديلة موثّقة إن ثقلت المكتبة*: الانضمام عبر متصفح داخلي.
- اختبار قبول: مكالمة صوت/فيديو بين جهازين خلف شبكتين منزليتين مختلفتين.

### C. الفوترة والدفع الحقيقي
- `apps/billing/gateways.py`: تجريد `PaymentGateway` + `MoyasarGateway` (secret key من env، إنشاء دفعة، تحقق توقيع webhook، استرداد) + `SandboxGateway` للاختبار. مفاتيح: `MOYASAR_SECRET_KEY`, `MOYASAR_PUBLISHABLE_KEY`, `PAYMENT_GATEWAY=moyasar|sandbox`.
- ربط `PaymentTransaction` الموجود + تحديث حالة `Invoice` من webhook **idempotent** (بـ event/معرّف المعاملة) عبر `invoice.process_payment()` الحالي.
- `InsuranceService`: حذف `random` — حالة "مقدّم للمراجعة" افتراضياً + قرارات عبر سياسة قابلة للتهيئة (نسبة تغطية من `InsuranceProvider`) + نقطة تثبيت لمزود خارجي لاحقاً.
- 12+ اختباراً: webhook بتوقيع صحيح/فاسد، تكرار event، سيناريو رفض/قبول تغطية جزئية.

### D. HL7/FHIR — واجهة عامة قابلة للربط
- استبدال المحلل اليدوي بمكتبة **hl7apy**: استيراد `ADT^A01/A08` (مريض) و`ORU^R01` (نتائج مختبر) → النماذج المحلية، مع رفض الرسائل غير المدعومة بوضوح.
- **كتابة FHIR R4**: `POST /api/v1/interoperability/fhir/Patient` (استيراد) + `GET .../fhir/Bundle?patient=` (تصدير مريض كامل) — بنفس قيود `accessible_patients` والتدقيق الحاليين.
- **عميل صادر قابل للتهيئة**: `FHIR_UPSTREAM_URL` + `FHIR_UPSTREAM_TOKEN` (فارغ = معطّل) — مهمة Celery تزامن/تدفع المورد للنظام الشريك مع إعادة محاولة وتدقيق `FHIR_OUTBOUND_SYNC`.
- اختبارات برسائل HL7 عينات + Bundle صالح الفحص.

### E. إكمال الأندرويد (الشاشات الاسمية)
- Telemedicine: تفاصيل + دردشة + انضمام مكالمة (من B). Analytics: إضافة `security/activity-feed` الموجودتين. Profile: تعديل بيانات + رفع صورة إلى `patients/files`/Media بدل ui-avatars (إغلاق N12).
- شاشات مفقودة نقاطها موجودة في الخادم: استعادة كلمة المرور، تسجيل/إدارة 2FA، تفضيلات الإشعارات، فحص تفاعلات دوائية عبر الخادم (`pharmacy/interactions/check/`).
- حذف الشيفرة الميتة (N14).

### F. إكمال الويب
- **مكوّن MFA مشترك واحد** (`components/MfaSettings.tsx`) يستبدل النسخ الثلاث.
- **i18n** بـ react-i18next (ar افتراضي، en) — يبدأ بالهيكل العام + الصفحات المشتركة، وربط مبدّل اللغة الحقيقي؛ حذف المبدّل الزائف أو تفعيله.
- **اختبارات Vitest + RTL**: authStore، client.ts (تجديد/403 codes)، شاشة دخول، مكون MFA. هدف بداية: ~30 اختباراً.
- كتالوج التقارير من `reportsAPI.list()` بدل التكرار في `Reports.tsx`؛ a11y للنوافذ (role/focus-trap عبر `common/Modal.tsx`).

---

## 4. ميزات متقدمة مقترحة (لكل قسم)

| القسم | الميزة | المبرر التشغيلي |
|---|---|---|
| الإشعارات | Web Push (VAPID) للويب + ملخص يومي/أسبوعي مجمع عبر Celery Beat | يكمل FCM الموجود لتغطية المنصتين |
| التقارير | جدولة تقرير دوري (أسبوعي/شهري بالبريد) من صفحة Reports | قيمة إشرافية للإدارة |
| الفوترة | كشف فحص تعارض الجرعات/الأدوية على الخادم (نقطة `interactions/check` موجودة — إثراء ببيانات تفاعلات) | سلامة المريض |
| الذكاء الاصطناعي | تحذير جرعات ذكي خلف فحص الدور + إخفاء الهوية الموجود | تعزيز سريري بلا مخاطرة PHI |
| النسخ الاحتياطي | تدريب استعادة آلي شهري (restore drill) يتحقق من أحدث نسخة ويرفع نتيجتها للوحة | ثقة تشغيلية موثقة |
| المراقبة | لوحة Grafana جاهزة (موجود provisioning) + تنبيه عند فشل سلسلة التدقيق أو تعطل TURN | إدارة حوادث |
| الأمان | عرض "الجلسات النشطة + إنهاء عن بعد" في الأندرويد (النقاط موجودة في `security/urls.py:30`) | توازن مع الويب |
| المرضى | تصدير Bundle FHIR كامل للمريض عن بياناته (حق المريض في النقل) | امتثال |

---

## 5. خارطة الطريق (Roadmap)

### المرحلة 0 — تثبيت (قبل أي شيء آخر)
بنود القسم 2 كاملة (P0 ثم P1): إصلاح تدفق الرموز والطابور السام، حذف مسار SmarterASP، تنظيف المستودع، توحيد Docker.
**معيار الخروج**: الاختبارات الثلاثة كلها خضراء + تدفق تجديد رمز يصمد + مستودع نظيف.

### المرحلة 1 — نشر VPS الإنتاجي
بناء الحزمة على VPS: compose كامل (db, redis, backend/daphne, celery worker+beat, coturn, nginx/TLS, prometheus, grafana)، مفاتيح إنتاج حقيقية (ENCRYPTION_KEY, AUDIT_LOG_HMAC_KEY, SECRET_KEY, Moyasar, FCM, GEMINI, TURN secret)، نسخ احتياطي خارجي مفعّل، سكربت فحص ما بعد النشر (health/live+ready، اتصال ws، إشعار تجريبي، مكالمة عبر TURN).
**معيار الخروج**: نشر يعيد إنتاجه من صفر من المستودع وحده + DEPLOYMENT.md محدَّث بمخطط الطوبولوجيا الفعلي.

### المرحلة 2 — الوحدات الاسمية تصبح حقيقية
القسم 3 بالترتيب: A (مزامنة) → C (فوترة) → B (فيديو+TURN) → D (FHIR). كل وحدة بفرعها واختباراتها.
**معيار الخروج**: مكالمة بين شبكتين منزليتين، دفعة sandbox ناجحة مع webhook، دفعة مزامنة دون اتصال تُستوعب بلا تكرار، استيراد/تصدير FHIR صالح.

### المرحلة 3 — إكمال المنصتين
القسم 3.E (أندرويد) و3.F (ويب: MFA/i18n/اختبارات/a11y).
**معيار الخروج**: لا شاشة اسمية في أي منصة؛ مجموعتا الاختبارات تنموان؛ i18n يعمل فعلياً.

### المرحلة 4 — الإطلاق
- تنفيذ `docs/PLAY_STORE_CHECKLIST.md` (سياسة خصوصية، Data Safety، فيديو إذن الإشعارات) + رفع نسخة موقّعة عبر `android-release.yml`.
- مراجعة أمنية ختامية: bandit/semgrep نظيفة، حرس الإنتاج بلا تحذيرات، فحص صلاحيات شامل لكل نقطة جديدة.
- اختبار حمل أولي (k6 على نقاط القوائم + البحث) وتثبيت سقوف `TRUSTED_PROXY_COUNT`/`METRICS_ALLOWED_IPS` للبيئة.
- تحديث README بأرقام حقيقية من آخر CI، وسم `v1.0.0`، وإصدار ملاحظات.

---

## 6. المخاطر والتبعيات

| الخطر | التخفيف |
|---|---|
| NPHIES/التأمين الإقليمي يتطلب اعتماداً رسمياً | التجريد `PaymentGateway`/`InsurancePolicy` — التبديل لاحقاً بلا إعادة بناء |
| ثقل WebRTC الأصلي في الأندرويد | خطة بديلة موثقة (انضمام عبر WebView) دون كسر عقد الإشارات |
| كوكي refresh عبر نطاقين إن بقيت طوبولوجيا منفصلة | توحيد الأصل في القسم 2-8 يحسمها مسبقاً |
| سياسات Play على `SCHEDULE_EXACT_ALARM` | الوضع الحالي موثق ومتوافق (setWindow fallback) — لا تغيير |
| تعارض ترحيلات عند إضافة `client_op_id` لجداول موجودة | قيم null مسموحة للسجلات القديمة + فهرس جزئي فريد |

## 7. أسئلة مفتوحة
لا يوجد شيء يحجب التنفيذ. القراران المتبقيان (بوابة الدفع، هدف FHIR) حُسما ببدائل افتراضية موثقة أعلاه بعد إسكات السؤالين، وكلاهما قابل للتبديل دون تغيير بنيوي.
