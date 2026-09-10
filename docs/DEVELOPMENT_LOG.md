# 🚀 SecureMed Development Log

---

# Phase 4o — زر حذف الحساب داخل التطبيق (2026-09-09)

> التحقق: `compileDebugKotlin` + `testDebugUnitTest` (**63 اختباراً**:
> 59 + 4 في `DeleteAccountViewModelTest`) + `lintDebug` خضراء.

## 1. مسار الحذف من الإعدادات

- ✅ `SecureMedApi.deleteAccount` (`DELETE auth/account/` بجسم كلمة
  المرور) و`SecureMedRepository.deleteAccount`: نجاح الخادم **شرط**
  للمسح المحلي — فشل الاستدعاء يعيد رسالة الخادم ولا يمسح شيئاً
  (مسحٌ بلا تعطيل كان سيقول «حُذف» والحساب حي). النجاح يشغّل المسح
  الكامل نفسه: منبهات، Room، توكنات، كاش — ثم `Result.success`.
- ✅ صف «حذف الحساب» في نهاية شاشة الإعدادات (بعد فاصل — منطقة خطر
  بعيدة عن الروتين)، حوار تأكيد بكلمة مرور (إظهار/إخفاء) يمنع الإرسال
  الفارغ ويعرض رسالة الخادم عبر `ApiErrors` بلا إغلاق الحوار، مع
  مؤشر تقدم في زر التأكيد.
- ✅ `DeleteAccountViewModel` بحالة مسطحة (`deleted` راية توجيه تنجو
  من `clearMessage` — الشاشة تقرأها في LaunchedEffect قد يسبق مستخدم
  متسرّع)؛ `MainActivity` يمرر `onAccountDeleted` يرفع قفل الخمول
  (`liftAppLockForSignedOut` في AuthViewModel) ويوجه لشاشة الدخول
  بمسح المكدس كاملاً.

## 2. ملفات جديدة/معدَّلة

| الملف | التغيير |
|---|---|
| `data/api/SecureMedApi.kt` | +deleteAccount |
| `data/SecureMedRepository.kt` | +deleteAccount (شرط نجاح الخادم ثم مسح كامل) |
| `ui/screens/DeleteAccountViewModel.kt` | جديد |
| `ui/screens/SettingsScreen.kt` | +صف منطقة الخطر +حوار كلمة المرور |
| `ui/MainActivity.kt` | +onAccountDeleted |
| `ui/AuthViewModel.kt` | +liftAppLockForSignedOut |
| `app/src/test/.../DeleteAccountViewModelTest.kt` | جديد — 4 |

## ما تبقى من قائمة Play (كله خارج الشيفرة)

صفحة ويب الحذف العامة، نشر سياسة الخصوصية، أسرار CI الأربعة، نموذج
Data Safety، فيديو تعريف إذن التنبيهات الدقيق، Store listing + حساب
مراجع — كلها موثقة في `docs/PLAY_STORE_CHECKLIST.md`.

---

# Phase 4n — نقطة حذف الحساب (متطلب Play، إغلاق الشيفري الوحيد المتبقي) (2026-09-09)

> التحقق: **402 اختباراً خادمياً ناجحاً** (7 جديدة في
> `tests/test_account_deletion.py`).

## 1. `DELETE auth/account/` — `DeleteAccountView`

- ✅ تحقق كلمة المرور إلزامي — جلسة مسروقة غير مقفلة لا تمحو الحساب.
- ✅ **تعطيل لا حذف**: `is_active=False` — صفوف PHI تحمل معرّف
  المستخدم في سلاسل `created_by`، وسلسلة تدقيق التحقق تعتمد عليها؛
  الحذف الفيزيائي كان إما كاسحاً للـ PHI أو يتيمها.
- ✅ `SessionManager.force_logout_user` — خروج كل الأجهزة + ختم زمن
  الإبطال الذي يفرّق `BoundJWTAuthentication` التوكنات الميتة من
  الجديدة.
- ✅ حدث تدقيق `USER_DEACTIVATED` بتفصيل السبب.

## 2. ثغرة مصاحبة أُغلقت: `LoginSerializer` لا يفحص `is_active`

- ✅ مستخدم معطَّل بكلمة مروره الصحيحة كان يعبر الدخول عادياً (200) —
  الحذف الذاتي لم يكن يمنعه فعلياً. الإصلاح في
  `LoginSerializer.validate`: فحص `is_active` **قبل** مقارنة كلمة
  المرور — الحساب الميت بكلمة مرور صحيحة يُرفض برسالة «غير مفعّل»،
  وبكلمة خاطئة برسالة الاعتماد المعتاد (لا كشف وجود الحساب).

## 3. اختبارات (7) — `tests/test_account_deletion.py`

كلمة مرور مفقودة/خاطئة تُرفض دون تعطيل؛ التعطيل بلا حذف فيزيائي؛
إنهاء كل الجلسات + ختم الإبطال؛ أثر التدقيق؛ الدخول بعد الحذف مرفوض
(وهي التي كشفت ثغرة السيريلايزر)؛ endpoint محمي بالمصادقة.

## 4. ملفات جديدة/معدَّلة

| الملف | التغيير |
|---|---|
| `backend/apps/accounts/views.py` | +`DeleteAccountView` |
| `backend/apps/accounts/urls.py` | +`auth/account/` |
| `backend/apps/accounts/serializers.py` | +فحص is_active في الدخول (إغلاق ثغرة) |
| `backend/tests/test_account_deletion.py` | جديد — 7 اختبارات |
| `docs/PLAY_STORE_CHECKLIST.md` | §2 الشيفرة منجزة |

**قائمة Play: لم يتبقَّ منها إلا عمل Console/ويب (صفحة حذف عامة، زر
التطبيق، نشر السياسة، الأسرار، Data Safety، الفيديو) — كلها خارج
الشيفرة وموثَّقة في القائمة.**

---

# Phase 4m — إغلاق 4-4 و4-5 (2026-09-09)

> التحقق: `compileDebugKotlin` + `testDebugUnitTest` + `detekt` + `lintDebug`
> خضراء (لا تعديلات شيفرة في هذه الجلسة — تدقيق فقط).

## 1. 4-4 · تدقيق الوصول وRTL (بلا عيب حرج)

- ✅ **contentDescription**: مسح آلي (سكربت مؤقت حُذف) وجد 13 أيقونة
  بحوصلة null — 5 زخرفية داخل FAB/بطاقات بنص (null صحيح عمداً)،
  والأزرار الأيقونية الفعلية (رجوع/حذف/رفع/حجز) كلها موصوفة نصاً
  عربياً. لا إصلاح مطلوب.
- ✅ **RTL**: صفر أيقونة اتجاهية غير `AutoMirrored`، صفر padding
  اتجاهي، صفر AbsoluteAlignment — الانعكاس بنيوي (`supportsRtl`).
- ✅ **تكبير الخط**: كل الأحجام `sp` عبر `Typography` مع lineHeight،
  لا fontSize متجمدة خارج الثيم.
- ✅ **مناطق اللمس**: لا هدف لمس قابل داخل < 48dp.
- حدّ مسجَّل: Accessibility Scanner الحي يحتاج جهازاً — جزء قبول
  الإصدار، لا جلسة شيفرة.

## 2. 4-5 · `android/README.md` — جديد

- ✅ متطلبات البناء (JDK 17 مع سبب حظر JDK 21+ لـ detekt).
- ✅ جدول عنوان الـ API وقواعده (HTTPS للإنتاج إلزامي: loopback النصي
  يعطّل الـ pinning).
- ✅ التوقيع: 4 خصائص خارج المستودع، تحذير البناء غير الموقَّع، v1
  معطَّل/v2+v3 مفعلة، توليد keystore أول مرة مع تحذير ضياع المفتاح.
- ✅ **استخراج هاش شهادة التوقيع** بطريقتين (`keytool -list` و
  `apksigner verify` على المُنتَج) + الفرق عن debug، **والتمييز**
  بينه وبين معرّف الجهاز (`installId`) الذي يربط الخادم الجلسة —
  «هاش التثبيت» في صياغة البند كان ملتبساً بين الحالتين.
- ✅ خط الإصدار بالوسم + أسراره + الإحالة لقائمة Play، وشجرة المصادر.

## المرحلة 4 صارت: 4-1 ✅ · 4-2 ✅ · 4-3 [~ Console work] · 4-4 ✅ · 4-5 ✅

---

# Phase 4l — قائمة تحقق سياسات Play (إغلاق 4-3) (2026-09-09)

> التحقق: `processDebugMainManifest` + `processDebugManifest` ناجحان،
> والـ manifest المدموج بعد التعديل فيه `SCHEDULE_EXACT_ALARM` وحده —
> تأكيد مزدوج (مصدر + مدموج بعد `--rerun-tasks`).

## 1. `docs/PLAY_STORE_CHECKLIST.md` — جديد

- ✅ نموذج Data Safety كجدول بيانات فعلي: حساب، PHI، بصمة جهاز
  (`X-Device-Fingerprint` لربط الجلسة)، IP، سجلات — **بلا مواقع، بلا
  مشاركة مع الغير**، ولا تُجمع بيانات بيومترية (البصمة محلية فقط).
- ✅ سياسة الخصوصية + **متطلب حذف الحساب**: الخادم لا يعرض نقطة نهاية
  حذف حساب (`accounts/urls.py`) — مسجَّل كنقص خادمي مطلوب قبل الرفع.
- ✅ الأذونات الثمانية، كلٌّ بمرجعه، والأهم: **`USE_EXACT_ALARM` حُذف**
  (منح تلقائي ممنوع لهذا الصنف) و`SCHEDULE_EXACT_ALARM` بقي مع
  الترحيل الموجود إلى نافذة غير دقيقة، وإجراء تعريفه في Console
  (نموذج + فيديو جرعة مستخدمة التعريف).
- ✅ إضافات PHI: `data_extraction_rules` موسَّعة (database/file/external
  مستثناة من cloud-backup وdevice-transfer) بعد أن كانت sharedpref
  وحدها؛ و`fullBackupContent="false"` موجود أصلاً.
- ✅ متطلبات المتجر: وصف طبي صحيح (أداة سير عمل مؤسسية لا تشخيص
  ذاتي)، حساب مراجع بلا MFA، تصنيف IARC القياسي.

## 2. ملفات جديدة/معدَّلة

| الملف | التغيير |
|---|---|
| `docs/PLAY_STORE_CHECKLIST.md` | جديد — القائمة التنفيذية |
| `android/app/src/main/AndroidManifest.xml` | -USE_EXACT_ALARM +تعليق سياسة |
| `android/app/src/main/res/xml/data_extraction_rules.xml` | +استثناءات database/file/external |
| `android/DEVELOPMENT_PLAN.md` | 4-3 [~] → عمل Console متبقٍ |

## ما يتبقى للرفع الأول (عمل خارج الشيفرة — القائمة تفصّله)

1. نقطة نهاية حذف الحساب + صفحة ويب.
2. نشر سياسة الخصوصية على نطاق الإنتاج.
3. أسرار CI الأربعة (keystore) ثم أول وسم ينتج AAB موقَّعاً (4-2).
4. تعبئة Data Safety + تعريف SCHEDULE_EXACT_ALARM بفيديو.
5. Store listing + حساب مراجع.

---

# Phase 4k — خط الإصدار (إغلاق 4-2) (2026-09-09)

> التحقق: detekt **يخضل** مع baseline 21 إدخالاً، و`dependencyUpdates` يُنتج
> تقريره، و`compileDebugKotlin` + `testDebugUnitTest` خضراء. البناء الموقَّع
> نفسه يجري في CI (الأسرار ليست على هذه الآلة، والقرص المحلي شبه ممتلئ).

## 1. `.github/workflows/android-release.yml`

- ✅ مُشغَّل: وسم `v*` أو `workflow_dispatch` باسم نسخة يدوي.
- ✅ versionName من الوسم (v1.4.2 → 1.4.2) وversionCode حسابياً
  (major×10000 + minor×100 + patch → 10402).
- ✅ keystore يُفك من `ANDROID_KEYSTORE_BASE64` ويُكتب في android/
  وقت التشغيل، وكلمات المرور من أسرار منفصلة — لا مادة مفتاح في git.
- ✅ السلسلة: detekt (حاجز) → testDebugUnitTest (حاجز) → bundleRelease
  بـ `-PSECUREMED_VERSION_NAME/CODE` → `apksigner verify` على الـ AAB
  (توقيع غائب = خطوة فاشلة صارخة لا رفع صامت) → أثر + GitHub Release
  بملاحظات مولَّدة.

## 2. detekt في الشجرة

- ✅ `detekt.yml` موثَّق قراراً بقرار: WildcardImport وFunctionNaming
  وMatchingDeclarationName والصيد العام للاستثناءات مطفأة بأسباب
  مسجَّلة (اتفاقات Compose والشيفرة القائمة وسياسة التدهور بلا انهيار).
- ✅ `detekt-baseline.xml` (21 إدخالاً): الموجود مجمَّد، وأي ملاحظة
  **جديدة** من نفس القاعدة تفشل الوسم — الخط يمنع التراجع ولا يعاقب
  التاريخ.
- ✅ إصلاح بيئي: detekt المضمَّن يرث هدف JVM من JDK المشغِّل — على JDK 24
  كان يتلقى `--jvm-target 24` غير مدعوم في 1.23.x — فثُبِّت 17 في
  `Detekt` و`DetektCreateBaselineTask`.
- ✅ درس ملف config: قاعدتان كُتبتا في مجموعات خاطئة (NamingConventions
  داخل style، LoopWithTooManyJumpStatements داخل complexity) فرفضهما
  detekt — أسماء القواعد تُتَّبع كما يعرّفها detekt لا كما يفترض القارئ.

## 3. فحص التبعيات

- ✅ `com.github.ben-manes.versions` 0.51.0 + خطوة `dependencyUpdates`
  في الوسم (معلوماتية) — يسمّي القديم ليقرره إنسان قبل الوسم، بعيداً
  عن ثِقَل ماسحات NVD.
- ✅ خيار ktlint: لا يُضاف — detekt يغطي حصته في هذه الشيفرة، و
  إضافة مُنسِّق ثانٍ يعني قاعدتي تنسيق متنازعتين.

## 4. تجاوز النسخ في build.gradle.kts

- ✅ `-PSECUREMED_VERSION_NAME/-PSECUREMED_VERSION_CODE` يتجاوزان
  versionName/versionCode؛ البناء المحلي يبقى على 1/1.0.0.

## ملفات جديدة/معدَّلة

| الملف | التغيير |
|---|---|
| `.github/workflows/android-release.yml` | جديد — خط الإصدار |
| `android/detekt.yml` + `detekt-baseline.xml` | جديد |
| `android/build.gradle.kts` | +detekt +versions plugins |
| `android/app/build.gradle.kts` | +detekt/versions +تجاوز النسخ +jvmTarget pins |
| `android/DEVELOPMENT_PLAN.md` | 4-2 [x] |

## أسرار CI المطلوبة قبل أول وسم

- `ANDROID_KEYSTORE_BASE64`، `ANDROID_KEYSTORE_PASSWORD`،
  `ANDROID_KEY_ALIAS`، `ANDROID_KEY_PASSWORD`.

---

# Phase 4j — إغلاق 4-1: اختبار قاعدة «الجلسة الخاصة» (2026-09-09)

> التحقق: **364 اختباراً خادمياً ناجحاً** (12 جديدة في
> `tests/test_session_security.py`). الأندرويد لم يُمَس.

## 1. القاعدة التي اختُبرت

`SessionManager.is_session_valid` تقارن بصمة الطلب **بجلسة المتصل وحدها**
(عبر `session_id`) — لا بكل جلسات المستخدم الحية. المقارنة الجَمعية كانت
تجعل دخولاً ثانياً (يُخلِّي جلسة المتصل بحدّ الجلسة المتزامنة = 1) أو
تفريغ الكاش يبدوان سرقة، و`reject_if_hijacked` يجيب الخلل بـ
`force_logout_user` — أي خروج الحساب كله من جهاز لهاتفه. لا اختبار في
المستودع كان يمسّ `SessionManager` قبل هذا الملف.

## 2. ما يثبته الاختبار (12 حالة)

- ✅ المطابقة بجلسة المتصل → صالحة، و`reject_if_hijacked` لا يرفض.
- ✅ عدم المطابقة → رفض + إبطال كامل (مسح `active_sessions` + تسجيل
  زمن الإبطال في `token_denylist` الذي يفرّق التوكنات الملغاة من
  اللاحقة لها).
- ✅ **الانحدار الرئيسي**: جلسة مُخلَّاة بحدّ الجلسة المتزامنة → صالحة
  (المقارنة الجَمعية كانت ترفضها وتخرج الحساب كله).
- ✅ تفريغ الكاش بعد التسجيل → صالحة. غياب ترويسة البصمة → صالحة
  (ربط JWT يغطي). جلسة بلا بصمة مسجَّلة → صالحة. متصل غير مصادق → صالح.
- ✅ دورة الحياة: `register_session` يحجب الجلسة السابقة (الحد = 1)،
  `end_session` ينهي جلسة الخيار ويُبقي الأخرى **بلا** تماس
  `force_logout_user`، يفرّغ المفتاح عند آخر جلسة، ويبقى no-op بلا
  معرّف. و`force_logout_user` يُسجل الإبطال ويُفرغ الجلسات.

## 3. ملف جديد

| الملف | المحتوى |
|---|---|
| `backend/tests/test_session_security.py` | 12 اختباراً لقاعدة الجلسة الخاصة ودورة حياة الجلسات |

**بند 4-1 مُغلق** (الباقي الوحيد كان هذا الاختبار؛ «تشغيل الحزمة في CI»
مصيره بند 4-2 خط الإصدار). المجموعة الخادمية: 352 → 364.

---

# Phase 4i — تغطية بنود 4-1 الثلاثة (2026-09-09)

> التحقق: `compileDebugKotlin` + `testDebugUnitTest` (**59 اختباراً**: 46 + 13
> جديدة في 3 أصناف) + `lintDebug` خضراء. لا تغييرات خادمية.

## 1. طبقة التشفير — `CacheCryptoTest` (5 اختبارات)

- ✅ الخيط المفصلي: منطق غلاف SMEDC1 سُحب من دوال Keystore إلى
  `seal`/`open` بمفتاح صريح — الصيغة على القرص كاملةً قابلة للاختبار
  بمفتاح برمجي، وطبقة Keystore تظل رقيقة.
- ✅ مثبَّت: دورة تشفير/فك، تمييز ملف قديم نصي (بلا غلاف)، رفض تلاعب
  بالـ GCM tag، مفتاح لا يطابق، غلاف مقطوع — والعقد «null لا throw».

## 2. الموديلات مقابل أجسام خادمية حقيقية — `ModelDeserializationTest` (5)

- ✅ أجسام JSON بأسماء حقول المُسلسلات الفعلية (وليس أمنيات العميل):
  `MedicalRecord` بـ `created_by_name: null` وحقل مجهول مستقبلي،
  `Notification` بحمولة `data` **رقمية**، `Appointment` بالأسماء
  الصحيحة، `RefreshResponse` بلا `refresh`، وطلب مختبر كامل.
- ✅ **كشف مباشر أثناء الكتابة**: `Notification.data` بصيغة `JsonObject`
  كان سيرفض رقماً حتى بعد إصلاح م10 (الرقم ليس كائناً) — صارت
  `JsonElement` فتقبل أي قيمة JSON. الاختبار أثبت قيمته فوراً.

## 3. عقد تجديد التوكن — `RefreshContractTest` (3)

- ✅ الأجسام الثلاثة الموثقة لـ `auth/refresh/`: دوران كامل (access+refresh)،
  بلا دوران (الجسم الذي كان يمحو جلسة مستخدم — درس 2-7)، وسلسلة فارغة.
  كلها تفك بنجاح، وعقد «الجلسة تبقى عند غياب الدوران» مثبَّت.

## الباقي من 4-1

- اختبار Django لقاعدة «الجلسة الخاصة» في `SessionManager` (خادمي).
- تشغيل الحزمة في CI.

## ملفات جديدة/معدَّلة

| الملف | التغيير |
|---|---|
| `data/local/CacheCrypto.kt` | +seal/open بمفتاح صريح (المنطق مفصلي) |
| `app/src/test/.../CacheCryptoTest.kt` | جديد — 5 |
| `app/src/test/.../ModelDeserializationTest.kt` | جديد — 5 |
| `app/src/test/.../RefreshContractTest.kt` | جديد — 3 |
| `data/model/Models.kt` | Notification.data: JsonObject → JsonElement |

---

# Phase 4h — نقل التخزين المحلي إلى Room (إغلاق 3-4) (2026-09-09)

> التحقق: الأندرويد `compileDebugKotlin` + `testDebugUnitTest` (**46 اختباراً**:
> 43 + 3 في `MedicationPlanEntityTest`) + `lintDebug` خضراء.

## 1. جداول الأدوية في Room (الإصدار 2→3)

- ✅ `MedicationPlanEntity` + `DoseLogEntity` في `data/local/room/` مع
  `MedicationDao` — البيانات الوحيدة التي كانت تُكتب دائماً في
  `LocalCache` صارت بمخطَّط واستعلامات، داخل قاعدة SQLCipher المشفَّرة.
- ✅ `MedicationStore` أعيد بناؤه فوق DAO **بنفس واجهته العامة** —
  `ReminderScheduler` ومسارات الإشعارات والمستقبلات لم تتغير، وأثر
  الترحيل محصور في طبقة التخزين.
- ✅ `SecureMedDatabase` → الإصدار 3 مع `medicationDao()` وثابت
  `MIGRATION_TARGET_VERSION`.

## 2. هجرة JSON→Room لمرة واحدة

- ✅ `MedicationStore.migrateFromLocalCache()` في `SecureMedApp.onCreate`
  — **قبل** أي فتح آخر للقاعدة: يقرأ ملفي الخطط والجرعات المشفَّرين
  (فكّ `CacheCrypto` صار مسؤولاً عن الترقية فقط كما طلب البند)،
  يستورد الصفوف إلى Room، ثم يحذف الملفين — الحذف بعد نجاح الاستيراد
  يجعل التهجئة idempotent.
- ✅ ترتيب الإقلاع مضبوط صراحة: `LocalCache.init` ثم `MedicationStore.init`
  ثم التهجئة ثم بقية التهيئة.
- ✅ `LocalCache.delete(key)` أُضيفت لسحب ملف مستورد بعينه.

## 3. إحكامات مصاحبة

- ✅ `logout` → `clearAll` يمسح جدولي الأدوية الآن — الخطط تحمل أسماء
  مرضى، ومسح الـ JSON عند الخروج كان يجب أن يتبع البيانات إلى Room.
- ✅ `logDose` كان يعيد كتابة كل سجل الجرعات لحفظ سطر واحد؛ الآن
  `INSERT ... REPLACE` على المفتاح الأساسي (planId|scheduledFor).
- ✅ عمود `times` المدمج (HH:mm مفصولة بفواصل) مع round-trip
  اختبارات — القائمة تُقرأ دائماً كاملة فلم تستحق جدولاً جانبياً.
- ✅ `DatabaseModule`: التعليق محدَّث — الإصدار ≥ 3 لم يعد محصَّناً بـ
  fallback تحريبي بالكامل (الصفوف الجهازية غير قابلة لإعادة الجلب)،
  فأي رفع إصدار لاحق يستوجب هجرات حقيقية وexportSchema.

## ملفات جديدة/معدَّلة

| الملف | التغيير |
|---|---|
| `data/local/room/MedicationEntities.kt` | جديد — جدولا + DAO |
| `data/local/room/SecureMedDatabase.kt` | v3 + medicationDao |
| `data/local/room/SecureMedDao.kt` | clearAll يغطي جداول الأدوية |
| `data/local/MedicationStore.kt` | معاد البناء فوق Room + تهجرة |
| `data/local/LocalCache.kt` | +delete(key) |
| `SecureMedApp.kt` | تسلسل الإقلاع + التهجرة قبل أي فتح |
| `di/DatabaseModule.kt` | تعليق سياسة الإصدارات محدَّث |
| `app/src/test/.../MedicationPlanEntityTest.kt` | جديد — 3 اختبارات |

**المرحلة 3 مكتملة بالكامل (3-1 حتى 3-6).**

---

# Phase 4g — عمليات الكتابة للشاشات الجديدة (2026-09-09)

> التحقق: الأندرويد `compileDebugKotlin` + `testDebugUnitTest` + `lintDebug` خضراء؛
> الخادم **344 اختباراً ناجحاً** (بلا تغييرات خادمية — التأكيد فقط).

## 1. ثلاث عمليات كتابة تكمل الشاشات الأربع (3-6)

- ✅ **إدخال نتيجة مختبر** — FAB في شاشة النتائج، حوار بمعرّف الطلب
  والقيمة (رقمية أو نصية أو كليهما — الرقمية تتفوق) وملاحظات؛
  `performed_by` هو المتصل، وعلامتا الحرج/غير الطبيعي تُحسبان خادمياً
  من مدى المرجع فلا يخمّن العميل علامة سريرية.
- ✅ **إدخال مريض لسرير** — زر «إدخال» على بطاقات الأسرّة **الحرة فقط**
  (حالة FREE)، حوار مريض (قائمة مرضى مُجلبَة مسبقاً) + تشخيص الدخول؛
  الرفض الخادمي لسرير غير حر أو مريض منوَّم يصل برسالته العربية،
  والنجاح يحدّث قائمتي الأسرّة والأقسام معاً (إشارة تحديث مزدوجة).
- ✅ **إنشاء فاتورة** — FAB في شاشة الفواتير: مريض + خصم + استحقاق +
  بنود متعددة (وصف/كمية/سعر وحدة) بتحقق محلي كامل؛ عرض حيّ للإجمالي
  التقديري مع تنبيه صريح أن الإجمالي النهائي والضريبة وتغطية التأمين
  تُحسب خادمياً.

## 2. البنية

- ✅ `OperationUiState` مشتركة (تقدم/رسالة/خطأ) + `OperationSnackbar`
  في الهيكل المشترك `PagedListScaffold` (وسيطا FAB وsnackbarHost
  اختياريان) — الشاشات الأربع تشارك نمط الكتابة والقراءة معاً.
- ✅ `PagedListScaffold` استقبل وسطاء كتابة بدون أن يكسر أي شاشة قراءة
  خالصة (التدقيق بلا FAB ورسائل).
- ✅ الواجهات الخادمية المستعملة: `LabResultCreateSerializer` (حقول
  order/numeric_value/text_value/notes)، `BedAssignmentCreateSerializer`
  (bed/patient/diagnosis_on_admission — bed وpatient إلزاميان)،
  `InvoiceCreateSerializer` (patient/discount/due_date/items ببنود
  description/quantity/unit_price).

## ملفات معدَّلة

| الملف | التغيير |
|---|---|
| `data/api/SecureMedApi.kt` | +createLabResult +assignBed +createInvoice +getActiveAssignments |
| `data/model/OperationsModels.kt` | +3 نماذج طلبات +BedAssignment |
| `data/SecureMedRepository.kt` | +3 عمليات كتابة +مصنع الإسنادات النشطة |
| `ui/screens/OperationsViewModels.kt` | حالة كتابة مشتركة + create flows |
| `ui/screens/OperationsScreens.kt` | حوارات الإدخال الثلاثة + ربط FAB/Snackbar |

**المتبقي من 3-6:** شاشة التقارير فقط.

---

# Phase 4f — الشاشات الناقصة: نتائج المختبر والأسرّة والفواتير والتدقيق (2026-09-09)

> التحقق: الأندرويد `compileDebugKotlin` + `testDebugUnitTest` + `lintDebug` خضراء؛
> الخادم **339 اختباراً ناجحاً** (بلا تغييرات خادمية — التأكيد فقط).

## 1. هيكل مشترك للقوائم المقروءة

- ✅ `PagedListScaffold`/`PagedListContent` في `OperationsScreens.kt`:
  تحميل أولي، خطأ الصفحة الأولى برسالة الخادم عبر `ApiErrors` + إعادة
  محاولة، فراغ، ومؤشر تقدم عند التمرير — نمط 3-3 نفسه لكل شاشة جديدة.

## 2. أربع شاشات جديدة (3-6)

- ✅ **نتائج المختبر** — `lab/results/` كانت نقطة ميتة كما وثّق البند؛ الآن
  قائمة مُرقَّمة تعرض القيمة، الحكم الخادمي (حرج/غير طبيعي/طبيعي) بلون
  كل صف، اسم من صادق على النتيجة، والملاحظات. الصف الحرج مظلَّل بالكامل
  وشارة «حرج».
- ✅ **الأقسام والأسرّة** — شريط أقسام بإشغال كل قسم (occupied/total من
  الخادم) فوق قائمة أسرّة مرقَّمة بألوان الحالات (متاح/مشغول/صيانة/
  تنظيف/محجوز). سؤال «أين يمكن إدخال هذا المريض؟» يُجاب من الشاشة.
- ✅ **الفواتير** — المريض والإجمالي مع الضريبة والمستحق وحالة السداد
  بلونها.
- ✅ **سجل التدقيق** — للمشرف والمدقق: بطاقته في لوحة التحكم **مُخفية
  لا معطَّلة** لغيرهم (`showAudit` من الدور: SUPER_ADMIN/HOSPITAL_ADMIN/
  AUDITOR)، ومن يدخل المسار مباشرة ترسم رسالة 403 الخادمية كحالة
  الشاشة — معيار القبول «تنجح في أدوارها وتعطي رسالة واضحة في غيرها»
  مستوفى بلا أي قفل إضافي في العميل.
- ✅ نمذجة: `OperationsModels.kt` (LabResult/Ward/Bed/Invoice/
  AuditLogEntry) — المعرَّف قاطع وبقية الحقول افتراضية، وفقاً لسياسة
  «عمود مُعاد تسميته يُسقط تسمية لا شاشة».

## 3. ملاحظات تنفيذ

- التنقل: 4 مسارات جديدة (LabResults/Wards/Invoices/Audit) و
  7 بطاقات خدمات على لوحة التحكم.
- ما بقي من البند: شاشة التقارير، وعمليات الكتابة (حجز سرير، فاتورة،
  إدخال نتيجة).

## ملفات جديدة/معدَّلة

| الملف | التغيير |
|---|---|
| `data/model/OperationsModels.kt` | جديد — 5 نماذج |
| `data/api/SecureMedApi.kt` | +lab/results +wards +beds +invoices +audit/logs |
| `data/SecureMedRepository.kt` | +5 مصانع ترقيم |
| `ui/screens/OperationsViewModels.kt` | جديد — 4 ViewModels |
| `ui/screens/OperationsScreens.kt` | جديد — هيكل مشترك + 4 شاشات |
| `navigation/Routes.kt` + `MainActivity.kt` | +4 مسارات |
| `ui/screens/Dashboard*.kt` | +7 بطاقات + showAudit |

---

# Phase 4e — ترقيم صفحات حقيقي للقوائم (إغلاق 3-3) (2026-09-09)

> التحقق: الأندرويد `compileDebugKotlin` + `testDebugUnitTest` (**43 اختباراً**:
> 40 سابقة + 3 جديدة في `ApiPagingSourceTest`) + `lintDebug` خضراء.
> لا تغييرات خادمية في هذه الجلسة.

## 1. مصدر ترقيم عام

- ✅ `data/paging/ApiPagingSource.kt` — مصدر Paging 3 واحد لكل قوائم الخادم:
  `loadPage: (page) -> PagedResponse<T>` والمفتاح التالي من غلاف `has_next`،
  بنفس عقيدة `PatientPagingSource` (واختباراته الجديدة تثبت: اشتقاق
  المفتاح التالي، توقف عند الصفحة الأخيرة، مرور الاستثناء إلى
  `LoadState.Error`).

## 2. ست قوائم حُوّلت

- ✅ الوصفات، المختبر، المواعيد، الاستشارات، الإشعارات، المستخدمون —
  كلها تابِع التحميل عند التمرير (مؤشر تقدم أسفل القائمة)، وإعادة محاولة
  عند فشل الصفحة الأولى برسالة الخادم عبر `ApiErrors`.
- ✅ الكتابة داخلها (حجز/إلغاء، صرف/إنشاء وصفة، تعليم مقروء، تفعيل/إيقاف)
  تُصدر `refreshRequests` والشاشة تنادي `refresh()` — الصفحات المُخزَّنة
  في `cachedIn` لا تتحديث وحدها.
- ✅ إشعارات: شارة غير المقروء صارت من `unread_count/` الخادمي — عدّها من
  قائمة مُرقَّمة كان سيبلّغ ناقصاً.
- ✅ لوحة التحكم: عدد المستخدمين من `count` الغلاف لا صفوف الصفحة الأولى.

## 3. ما بقي عمداً

- السجلات الطبية: صفحة المريض تقرأ التجميعة المقطوعة 100 سجل (ليست قائمة
  مُرقَّمة)، وقائمة القناة نادرة الطول فبقيت على القراءة المخزَّنة.
- القوائم المُحوَّلة شبكية بحت (ثمن الترقيم الموثق في البند)؛ قائمة
  المرضى وحدها تعمل دون اتصال من Room كما كانت.

## ملفات جديدة/معدَّلة

| الملف | التغيير |
|---|---|
| `data/paging/ApiPagingSource.kt` | جديد — مصدر عام |
| `app/src/test/.../ApiPagingSourceTest.kt` | جديد — 3 اختبارات |
| `SecureMedApi.kt` | +page لـ users/notifications/records |
| `SecureMedRepository.kt` | +7 مصانع ترقيم +getUsersTotalCount |
| `Lab/Telemedicine/Appointments/Pharmacy/Notifications/Users` ViewModels+Screens | تحويل إلى LazyPagingItems |
| `android/DEVELOPMENT_PLAN.md` | 3-3 [x] |

---

# Phase 4d — إغلاق بندي 3-1 و3-5 (2026-09-09)

> التحقق: الأندرويد `compileDebugKotlin` + `testDebugUnitTest` + `lintDebug` خضراء.
> لا تغييرات خادمية في هذه الجلسة.

## 1. حجز موعد من صفحة المريض (آخر بند مفتوح في 3-1)

- ✅ أيقونة تقويم في الشريط العلوي لصفحة المريض تفتح `BookingDialog` بمريض
  **مقفل** — اسمه يُعرض نصاً ثابتاً بدل قائمة الاختيار، فالحوار من هذا
  الموضع يختار الطبيب والنوع والأولوية والوقت فقط.
- ✅ `BookingDialog` صار `internal` بوسيط `lockedPatient` اختياري — شاشة
  المواعيد تستعمله كما هي بلا قفل، وصفحة المريض تمرر المريض الحالي.
- ✅ الأطباء يُجلبون قبل فتح الحوار (`prepareBookingData`) فلا يفتح الحوار
  على قائمة فارغة؛ وإن فشل الجلب فالحوار يظهر والرسالة الخادمية تشرح عند
  الإرسال.

## 2. إعلان مصير خطط الأدوية (إغلاق 3-5 وقرار «ب»)

- ✅ بطاقة إعلان فوق قائمة الخطط في شاشة الأدوية: «خطط الأدوية تتزامن مع
  الخادم ويراها فريق الرعاية. أما سجل الجرعات والالتزام فمحفوظ على هذا
  الجهاز فقط ولا يُشارك» — معيار القبول «لا تبقى ميزة تبدو مشتركة وهي محلية»
  مستوفى.
- ✅ ثمن قرار «ب» زال بحد ذاته: الخطط صارت نسخة مُزامَنة قابلة للاسترجاع
  من الخادم، فمحوها عند الخروج لم يعد فقداً بلا رجعة.

## ملفات معدَّلة

| الملف | التغيير |
|---|---|
| `android/.../screens/AppointmentsScreen.kt` | BookingDialog → internal + lockedPatient |
| `android/.../screens/PatientDetailScreen.kt` | +أيقونة حجز + ربط الحوار المقفل |
| `android/.../screens/PatientDetailViewModel.kt` | +createAppointment +prepareBookingData |
| `android/.../screens/MedicationsScreen.kt` | +بطاقة الإعلان (تزامن الخطط / محلية الجرعات) |
| `android/DEVELOPMENT_PLAN.md` | 3-1 [x]، 3-5 [x] |

**المرحلة 3 صارت مكتملة عدا 3-3 (ترقيم الصفحات — نصفها منجز) و3-4 (نقل
التخزين إلى Room).**

---

# Phase 4c — إكمال عمليات الكتابة: الوصفات وتعديل/حذف السجلات (2026-09-09)

> التحقق: **325 اختباراً خادمياً ناجحاً** (6 جديدة في `tests/test_medical_record_writes.py`)
> والأندرويد: `compileDebugKotlin` + `testDebugUnitTest` + `lintDebug` خضراء.
> (`test_backups.py` يبقى خارج الحساب — أعطاله بيئية على Windows وليست من الشيفرة.)

## 1. ثغرة خادمية أُغلقت قبل كشف التعديل/الحذف من التطبيق

- ✅ `MedicalRecordViewSet` لم يكن يعرّف `perform_update`/`perform_destroy` — الافتراضي
  في ModelViewSet لا يفحص شيئاً، فأي مستخدم مجازٍ للقراءة (بما فيهم دور VIEWER)
  كان يستطيع `PATCH`/`DELETE` أي سجل تراه قنواته. الحرس الجديد `_can_modify_record`
  يطبق قاعدة الإنشاء نفسها: مدراء دائماً، وإلا محرر أو أعلى في قناة السجل،
  والسجل بلا قناة (بعد حذفها SET_NULL) لا يُعدَّل إلا من مدراء.
- ✅ أحداث تدقيق جديدة: `MEDICAL_RECORD_UPDATED` و`MEDICAL_RECORD_DELETED`
  (وهذا الأخير يُسجَّل قبل الحذف حتى تبقى التفاصيل) و`PRESCRIPTION_CREATED` —
  الإنشاء كان خطوة دورة حياة الوصفة الوحيدة بلا أثر تدقيق. هجرة `audit.0006`.

## 2. إصلاح خادمي مصاحب: ردّ إنشاء الوصفة

- ✅ `PrescriptionCreateSerializer.Meta.fields` لم يكن يضم `id`، فجسم 201 كان
  بلا هوية ولا يمكن للعميل أن يعرف ما أنشأه إلا بإعادة جلب القائمة. أُضيف
  `id` (read-only).

## 3. الأندرويد — بند 3-1 أُكمل

- ✅ **إنشاء وصفة طبية** من شاشة الصيدلية (FAB): مريض من قائمة المرضى، وبنود
  أدوية متعددة تُبنى من فهرس الصيدلية `GET pharmacy/medications/` (نقطة كانت
  بلا أي مستهلك أندرويدي) — لكل بند: دواء بالمعرّف (الخادم يرفض الأسماء
  الحرة)، جرعة، تكرار، مدة بالأيام، كمية. التحقق محلي قبل الإرسال، والرسائل
  الخادمية عبر `ApiErrors`.
- ✅ **تعديل السجلات** (`PATCH patients/records/{id}/`): زر «تعديل» على كل
  بطاقة سجل يفتح حواراً محمّلاً بالقيم الحالية (النوع يُسترجع من التسمية
  المعربة مع سقوط إلى القيمة الخام).
- ✅ **حذف السجلات** (`DELETE`): زر «حذف» بلون الخطأ مع حوار تأكيد يذكر أن
  الحذف يُدقَّق — رسالة 403 لغير المصرّح تصل من الخادم، وفشل أي عملية لا
  يكتب شيئاً في الذاكرة المؤقتة (النجاح يعيد الجلب من التجميعة).
- ✅ `PharmacyViewModel` أعيدت كتابتها بنمط الحالة المسطحة (تقدم/رسالة/خطأ)
  بدل `runCatching` الصامت الذي كان يبتلع فشل الصرف.

## 4. ملفات جديدة/معدَّلة

| الملف | التغيير |
|---|---|
| `backend/apps/patients/views.py` | +`_can_modify_record`/`perform_update`/`perform_destroy` |
| `backend/apps/pharmacy/views.py` | +`perform_create` بتدقيق `PRESCRIPTION_CREATED` |
| `backend/apps/pharmacy/serializers.py` | +`id` في ردّ إنشاء الوصفة |
| `backend/apps/audit/models.py` + هجرة 0006 | +3 أحداث |
| `backend/tests/test_medical_record_writes.py` | جديد — 6 اختبارات |
| `android/.../api/SecureMedApi.kt` | +PATCH/DELETE records +createPrescription +getMedications |
| `android/.../model/Models.kt` | +MedicalRecordUpdateRequest |
| `android/.../model/PharmacyModels.kt` | +PrescriptionCreateRequest +PrescriptionItemRequest |
| `android/.../SecureMedRepository.kt` | +updateMedicalRecord +deleteMedicalRecord +createPrescription +getMedicationCatalog |
| `android/.../screens/Pharmacy*.kt` | حوار إنشاء وصفة ببنود + حالة مسطحة |
| `android/.../screens/PatientDetail*.kt` | أزرار تعديل/حذف + حواران |

## ما يحتاج جهازاً أو خادماً حياً

- دورة صرف وصفة أُنشئت من التطبيق: خصم مخزون فعلي ورسالة المخزون الناقص.
- سلوك 403 فعلي لمستخدم VIEWER عند محاولة تعديل/حذف من الواجهة.

---

# Phase 4b — عمليات الكتابة وإصلاح الإسناد السريري (2026-09-08)

> التحقق: **320 اختباراً خادمياً ناجحاً** (315 سابقة + 5 جديدة في
> `tests/test_patient_profile.py`؛ 8 أخطاء بيئية قديمة في `test_backups.py`
> — أذونات مجلد temp على Windows وقفل مجلد خارجي — تثبت على الشجرة النظيفة
> أنها ليست من شيفرة هذا العمل). الأندرويد: `compileDebugKotlin` +
> `testDebugUnitTest` + `lintDebug` خضراء.

## 1. إصلاح ع6 — إسناد السجلات في صفحة المريض (بند 3-2)

- ✅ صفحة المريض كانت تنادي `getMedicalRecords(null)` — القائمة العامة — فتعرض
  سجلات كل المرضى تحت اسم أي مريض. صارت تقرأ التجميعة الخادمية
  `GET patients/{id}/profile/` التي تقيّد السجلات بقنوات المريض × امتيازات
  المتصل (`PatientViewSet.profile` → `get_viewable_channels`).
- ✅ العميل: `PatientProfileResponse` (patient/records/channels/files/stats)،
  `SecureMedRepository.getPatientProfile` (قراءة مخزَّنة)، و
  `PatientDetailViewModel` معاد البناء على التجميعة مع قسم ملفات طبية جديد.
- ✅ **قفل القاعدة بخمسة اختبارات** (`tests/test_patient_profile.py`):
  سجلات مريضٍ آخر لا تظهر، تجميعة عدة قنوات لمريض واحد، منع اللاعضو،
  عضوٌ لا يرى قناة بلا عضوية، وتطابق كتلة `stats` مع الجسم.
- ✅ قرار (أ) في خطة الأندرويد أُغلق بخيار التجميعة الموجودة — بلا هجرة
  وبلا تعديل في `MedicalRecordViewSet`.

## 2. بند 3-1 — أول عمليات الكتابة من التطبيق

- ✅ **إصلاح مسبق حرج**: `MedicalRecordCreateRequest` كان يرسل `channel_id`
  والمُسلسِل يقبل `channel` — كل سجل معلّق كان يُرفض 400 للأبد. الحقل صار
  `channel`.
- ✅ **إنشاء سجل طبي** من صفحة المريض: حوار يقرأ قنوات المريض من التجميعة،
  أنواع `RecordType` الثمانية، حالة حرجة، وحالة تحميل — ورسائل 403 من
  `ApiErrors` بجسم الخادم العربي.
- ✅ **حجز موعد وإلغاؤه**: `POST appointments/` + `POST appointments/{id}/cancel/`
  مع حوار حجز (مريض/طبيب/نوع/أولوية/تاريخ/وقت/مدة) يجمّع المرضى
  والأطباء (`auth/users/?role=DOCTOR`)، وحوار إلغاء بسبب اختياري.
  رفض الوقت الماضي وتعارض الطبيب يصلان برسالة الخادم.
- ✅ **رفع ملف طبي** من تفاصيل القناة: `@Multipart POST patients/files/` عبر
  `OpenDocument`، بتحقق عميل من الامتدادات (jpg/jpeg/png/gif/pdf/dicom/dcm)
  وحدّ 20MB قبل الإرسال، وحوار بيانات وصفية (نوع/عنوان/وصف)، وSnackbar
  للنتيجة — فشل الرفع لا يكتب شيئاً في الذاكرة المؤقتة.
- ✅ `getDoctors()` — `auth/users/?role=DOCTOR` مقصور خادمياً بالنطاق الحوضي.

## 3. إصلاح م10 — حقولا تحطّم التحويل عند الحدّية

- ✅ `Notification.data`: `Map<String, String>?` → `JsonObject?` — حقل JSON
  حرّ على الخادم، وقيمة رقمية كانت تُسقط قائمة الإشعارات كلها (بلا أي
  مستهلك للحقول اليوم).
- ✅ `MedicalRecord.createdByName` صار قابلاً للإسناد الفارغ — `created_by`
  على الخادم قد يكون فارغاً — والموضعان اللذان يعرضانه يعرضان «غير معروف».

## 4. ملفات جديدة/معدَّلة رئيسية

| الملف | التغيير |
|---|---|
| `backend/tests/test_patient_profile.py` | جديد — 5 اختبارات إسناد |
| `android/.../api/SecureMedApi.kt` | +profile +upload multipart +create/cancel appointment +users?role |
| `android/.../model/Models.kt` | +PatientProfileResponse +AppointmentCreateRequest؛ إصلاح م10؛ channel_id→channel |
| `android/.../model/OtherModels.kt` | +MedicalFileDto |
| `android/.../SecureMedRepository.kt` | +getPatientProfile +uploadMedicalFile +create/cancelAppointment +getDoctors |
| `android/.../screens/PatientDetail*.kt` | معاد البناء على التجميعة + حوار إنشاء سجل + ملفات |
| `android/.../screens/Appointments*.kt` | حوار حجز + إلغاء + رسائل خادم |
| `android/.../screens/ChannelDetail*.kt` / `ChannelsViewModel.kt` | رفع ملفات + حالة رفع |
| `android/DEVELOPMENT_PLAN.md` | 3-2 [x]، 3-1 [~]، إغلاق قرار (أ)، م10 أُصلح |

## ما يحتاج جهازاً أو خادماً حياً (لم يُتحقَّق منه)

- دورة الحجز الفعلية مقابل خادم حيّ: تعارض الطبيب والوقت الماضي برسالة عربية.
- رفع ملف DICOM حقيقي يمر توقيع الملف الخادمي (sniffing).
- عدد سجلات صفحة المريض مقابل الويب لحساب حقيقي (معيار قبول 3-2).

---

# Phase 4 — Feature Expansion (2026-09-08)

> التحقق: **314 اختباراً ناجحاً** (296 سابقة + 18 جديدة في `tests/test_new_features.py`).
> ترحيلات جديدة: `patients.0002_patient_user`، `pharmacy.0002_medicationplan`،
> `notifications.0002_pushtoken`، `audit.0005_alter_auditlog_event_type`.
> بناء الأندرويد: `compileDebugKotlin` ناجح.

## ملاحظة تحقق مهمة

بند التدقيق القديم (SECUREMED_AUDIT_2026-09-04) عن الكاش وخدمة الملفات
والبحث العام وRefreshToken وسلسلة HMAC كانت **مُصلَحة بالفعل في الشجرة
الحالية** قبل هذه الجلسة — تحقّقنا من كل بند بالقراءة المباشرة ولم تُعاد
تنفيذه. الجديد في هذه الجلسة:

## 1. أمن وتشغيل

- ✅ **كشف السلوك الشاذ لسرعة الوصول للملفات** (`apps/core/anomaly.py`):
  عدّادات نافذة منزلقة (5د/1س) على الكاش المشترك، كل قراءة ملف طبي عبر
  `ProtectedMediaView` أو `MedicalFileViewSet` تُحتسب؛ تجاوز العتبة يولّد
  `SUSPICIOUS_ACTIVITY` + تنبيه Telegram + إشعار للمدراء (بتبريد 10 دقائق).
  عتبات قابلة للضبط عبر `PHI_ANOMALY_THRESHOLD_SCALE`.
- ✅ **Telegram**: `send_critical_alert()` عامة؛ نتائج المختبر الحرجة تُرسل
  فوراً لقناة الإدارة، وكل إشعار CRITICAL يُمْرَر تلقائياً إليها.
- ✅ **حدث تدقيق** جديد: `AI_INTERACTION_CHECKED` / `AI_INTERACTION_FAILED`.

## 2. الذكاء الاصطناعي

- ✅ **فحص التداخلات الدوائية** (`POST /api/v1/ai/interactions-check/`):
  محركان — قواعد `DrugInteraction` (مطابقة بالاسم، دائماً تعمل بلا مفتاح) +
  مراجعة Gemini إضافية مع الحساسية والأدوية الحالية. التحقق من ملكية المريض
  عبر `accessible_patients` — نفس قاعدة كل مسارات PHI.

## 3. دردشة القنوات (Phase 4 من خارطة الأندرويد)

- ✅ **خلفية**: `ChannelMessage` كانت موجودة، أُضيف `ChannelChatConsumer`
  (`ws/channel_chat/<id>/`) بنفس قاعدة `can_view`، ويحفظ عبر مسار REST نفسه.
- ✅ **أندرويد**: `ChannelChatScreen` مع جلب تدريجي `?after=` كل 5 ثوان،
  محجوزة في `Routes.ChannelChat` ومربوطة من شاشة تفاصيل القناة.

## 4. الإشعارات الفورية (FCM)

- ✅ **خلفية**: موديل `PushToken` + `POST/DELETE /api/v1/notifications/push/register/`
  + وحدة `apps/notifications/push.py` (FCM HTTP v1 عبر OAuth2 JWT — بلا
  تبعيات جديدة). التسليم للأولوية HIGH/CRITICAL فقط مع احترام ساعات الهدوء،
  وأفضل-جهد دائماً. إعداد: `FCM_PROJECT_ID` + `FCM_SERVICE_ACCOUNT_JSON`.
- ✅ **أندرويد**: `SecureMedPushService` + قناة إشعارات مخصصة؛ الاعتمادية
  `firebase-messaging` مضافة لكن التفعيل **اختياري** عبر
  `-PSECUREMED_FCM=true` مع `google-services.json` — غيابها لا يعطّل شيئاً.

## 5. بوابة المريض

- ✅ **إصلاح جذري**: `Patient.user` (OneToOne) — كان `appointments/views`
  يرشّح على `patient__user` وهو حقل غير موجود (FieldError لكل حساب PATIENT).
- ✅ **نقاط نهاية ذاتية** (`apps/patients/portal.py`):
  `GET /api/v1/patients/portal/` و`/portal/{appointments|invoices|lab-results|prescriptions|records}/`
  — قراءة فقط، مرتبطة بسجل المريض المرتبط بالحساب حصراً، وقراءة نتائج
  المختبر تُدقَّق.

## 6. تكامل FHIR

- ✅ **Observation** (`GET /api/v1/interoperability/fhir/Observation/`):
  LOINC من كتالوج المختبر، `valueQuantity/valueString`، نطاق مرجعي،
  تفسير HH/LL/A. **مقيّد دائماً** بعين المرضى المتاحين (الثغرة اكتُشفت
  أثناء كتابة الاختبار وأُغلقت)، ونتائج غير COMPLETED/VALIDATED لا تُصدَّر.
- ✅ `LabTest.loinc_coding()` و`LabResult.to_fhir()`.

## 7. مزامنة خطط الدواء

- ✅ **خلفية**: موديل `MedicationPlan` (الاسم مشفّر Fernet) +
  `GET/POST /api/v1/pharmacy/medication-plans/` — upsert عبر `source_id`
  (معرّف الخطة المحلية على الجهاز)، مقيّد بعين المرضى.
- ✅ **أندرويد**: `syncMedicationPlans()` (سحب ثم دفع) تلقائياً عند فتح
  شاشة الأدوية + يدوياً عبر التحديث؛ النسخة المحلية تبقى مصدر المنبهات.

## 8. المراقبة

- ✅ **Grafana + Prometheus**: provisioning جاهز في `deploy/grafana/` و
  `deploy/prometheus/`، مفعّل عبر `docker compose --profile observe up`
  (Grafana على 3001، لوحة "SecureMed — Operational Health").

## ملفات جديدة/معدّلة رئيسية

| الملف | التغيير |
|---|---|
| `apps/core/anomaly.py` | جديد — كشف السلوك الشاذ |
| `apps/notifications/push.py` | جديد — FCM HTTP v1 |
| `apps/notifications/models.py` | +PushToken |
| `apps/notifications/views.py`, `urls.py` | +register endpoint |
| `apps/notifications/utils.py` | +push/Telegram dispatch |
| `apps/channels/consumers.py`, `routing.py` | جديد — دردشة WebSocket |
| `apps/patients/portal.py` | جديد — بوابة المريض |
| `apps/patients/models.py` | +Patient.user |
| `apps/pharmacy/models.py` | +MedicationPlan |
| `apps/pharmacy/views.py`, `urls.py` | +medication-plans |
| `apps/lab/models.py` | +to_fhir, loinc_coding |
| `apps/interoperability/views.py`, `urls.py` | +FHIRObservationViewSet |
| `apps/ai/views.py`, `urls.py` | +interactions-check |
| `apps/security/telegram_service.py` | +send_critical_alert |
| `apps/audit/models.py` | +AI_INTERACTION_* events |
| `config/settings.py` | +FCM_* settings |
| `config/asgi.py` | +channels routing |
| `docker-compose.yml` | +prometheus/grafana |
| `android/.../push/SecureMedPushService.kt` | جديد |
| `android/.../screens/ChannelChatScreen.kt` | جديد |
| `android/.../Screens/medications sync` | Repository + ViewModel |
| `backend/tests/test_new_features.py` | جديد — 18 اختباراً |

## ما يحتاج إعداداً قبل التشغيل

1. **FCM**: `FCM_PROJECT_ID` + `FCM_SERVICE_ACCOUNT_JSON` في الخلفية،
   و`google-services.json` + `-PSECUREMED_FCM=true` في الأندرويد.
2. **Telegram**: `TELEGRAM_BOT_TOKEN` + `TELEGRAM_ADMIN_CHAT_ID` (موجود
   أصلاً في الإعداد).
3. **عتبة السلوك الشاذ**: اضبط `PHI_ANOMALY_THRESHOLD_SCALE` في المنشآت
   الغنية بالأشعة (قيمة أكبر = عتبات أعلى).
4. `python manage.py migrate` بعد السحب.

---

# Phase 2 (سابق)

## Summary of Enhancements

### 1. Database Enhancements
- ✅ Added 3 new apps: `notifications`, `analytics`
- ✅ Created `Notification`, `NotificationPreference`, `EmailLog` models
- ✅ Created `SystemMetric`, `UserActivity`, `SecurityDashboardStat` models
- ✅ Added `MedicalFile` model for medical image upload
- ✅ Created proper migrations for all new models
- ✅ Added database indexes for performance

### 2. Backend Enhancements
- ✅ **Pagination**: All APIs now use `SecureMedPagination` (20 items/page, max 100)
- ✅ **Filtering**: Advanced filtering with `django-filters` on all endpoints
- ✅ **Search**: Full-text search on all list endpoints
- ✅ **Ordering**: Customizable ordering via query parameters
- ✅ **File Upload**: Medical files (X-rays, MRIs) with validation
- ✅ **Notifications System**: Real-time notifications with:
  - User preferences (email, push, in-app)
  - Quiet hours support
  - Priority levels (LOW, MEDIUM, HIGH, CRITICAL)
  - Auto-generation on channel/permission events
- ✅ **Analytics Dashboard**: Comprehensive statistics:
  - User stats (total, active, by role)
  - Channel stats (by type, by priority, active)
  - Patient stats (total, new today/week)
  - Security stats (alerts, WAF blocks, failed logins, biometric logins)
  - Activity trends (last 8 days)
  - Real-time activity feed
- ✅ **Audit Logging**: All notification events are logged
- ✅ **Email Logging**: Track email delivery status

### 3. Frontend Enhancements
- ✅ **Dark Mode**: Full dark mode support with toggle
- ✅ **Analytics Dashboard**: New page with:
  - Real-time stats cards with trend indicators
  - Custom SVG charts (activity trend, channels trend)
  - Users by role with progress bars
  - Channels by type breakdown
  - Live activity feed
  - Auto-refresh every 30 seconds
- ✅ **Notifications Center**: New page with:
  - Filter tabs (all, unread, critical)
  - Notification cards with priority indicators
  - Mark as read / dismiss actions
  - Auto-refresh every 10 seconds
- ✅ **Real-time Updates**: Polling for notifications and dashboard data
- ✅ **Improved UI/UX**: Better loading states, animations, transitions
- ✅ **Responsive Design**: Mobile-optimized layouts

### 4. Android App Enhancements
- ✅ **Dark Mode**: Material 3 dynamic color scheme (light/dark)
- ✅ **Notifications Screen**: Full notifications list with:
  - Priority color indicators
  - Mark as read functionality
  - Empty state handling
- ✅ **Dashboard Enhancement**: Added notifications bell icon
- ✅ **New Models**: `Notification`, `DashboardStats` for analytics
- ✅ **API Extensions**: Notifications and analytics endpoints

### 5. New API Endpoints

#### Analytics
- `GET /api/v1/analytics/dashboard/overview/` - Dashboard statistics
- `GET /api/v1/analytics/dashboard/security/` - Security analytics
- `GET /api/v1/analytics/dashboard/activity-feed/` - Recent activity feed
- `GET /api/v1/analytics/activities/` - User activities list
- `GET /api/v1/analytics/metrics/` - System metrics

#### Notifications
- `GET /api/v1/notifications/` - List notifications
- `GET /api/v1/notifications/unread_count/` - Unread count
- `POST /api/v1/notifications/mark_all_read/` - Mark all as read
- `POST /api/v1/notifications/{id}/mark_read/` - Mark one as read
- `DELETE /api/v1/notifications/{id}/dismiss/` - Delete notification
- `GET/PUT /api/v1/notifications/preferences/` - User preferences

#### Medical Files
- `GET /api/v1/patients/files/` - List medical files
- `POST /api/v1/patients/files/` - Upload medical file
- `GET /api/v1/patients/files/{id}/` - File details
- `GET /api/v1/patients/files/{id}/download/` - Download file
- `DELETE /api/v1/patients/files/{id}/` - Delete file

### 6. Testing
- ✅ **96 tests still pass** (no regressions)
- ✅ All new APIs tested manually and verified working
- ✅ Dashboard overview returns real data
- ✅ Notifications system creates notifications on events
- ✅ Activity feed shows recent activities

### 7. File Count
- Backend: 30+ files (added notifications + analytics apps)
- Frontend: 18+ files (added Analytics + Notifications pages, theme store, hooks)
- Android: 20+ files (added Notifications screen, updated theme, models)
- Total: 175+ files

## Verification Results

```
Backend Tests: 96/96 passed ✅
Dashboard API: Working ✅ (returns real stats)
Notifications API: Working ✅ (unread_count = 0)
Activity Feed: Working ✅ (returns 3 recent activities)
WAF Protection: Working ✅ (blocks SQL injection)
JWT Auth: Working ✅ (RS256 in prod, HS256 in dev)
```

---

# 🛠️ Phase 3 — إصلاحات الإكمال النهائي (2026-08-30)

## ملخص الإصلاحات

### 1. Backend (Django)
- ✅ **إصلاح `vulnerability_scanner.py`**: استبدال `pkg_resources` (المحذوف من setuptools الحديث / Python 3.12) بـ `importlib.metadata` — كان يسبب `ModuleNotFoundError` عند فحص الثغرات.
- ✅ **إصلاح إيجابية كاذبة حرجة في WAF** (`apps/security/middleware.py`): كان جدار الحماية يفحص ترويسة `Referer` ضد أنماط SSRF (مثل `http://localhost`)، مما حجب **كل** طلبات المتصفح المشروعة من الواجهة الأمامية برمز 403 في بيئة التطوير. الآن تُفحص الترويسات ضد جميع أنماط الهجوم *ما عدا* SSRF (لأن Referer رابط مشروع بطبيعته)، بينما تُفحص معاملات الطلب والجسم ضد جميع الأنماط بما فيها SSRF — حيث توجد حمولات SSRF الفعلية.
- ✅ **إعادة تعيين كلمة مرور المدير** إلى `SecureMed@2026!` لتتوافق مع README وsetup.sh.
- ✅ **تعبئة قاعدة البيانات** عبر `scripts/seed_data.py`: 10 مستخدمين، 8 مرضى، 5 قنوات، 14 عضوية، 10 سجلات طبية.
- ✅ **96/96 اختبار ناجح** بعد الإصلاحات (بدون أي انحدارات).

### 2. Frontend (React + Vite + Tailwind)
- ✅ **إضافة `postcss.config.js` المفقود** (كان السبب الجذري لعدم تحميل أي تنسيقات Tailwind — كانت الصفحات تظهر HTML خام بدون تصميم).
- ✅ **إصلاح خطأ صياغة JSX** في `AnalyticsDashboard.tsx` (سطر 231): backtick ناقص في template literal.
- ✅ **إصلاح `extendedApis.ts`**: تصحيح الاستيراد (`import api from './client'`) وحذف إعادة تصدير `notificationsAPI` غير الموجودة.
- ✅ **إصلاح تعارض الأسماء** في `Users.tsx`: أيقونة `Users` من lucide-react كانت تتعارض مع مكوّن `Users` المحلي → أعيدت تسميتها `UsersIcon`.
- ✅ **إصلاح أخطاء TypeScript** (implicit any) في `Channels.tsx` و`ChannelDetail.tsx`.
- ✅ **حذف `src/tailwind.config.js` المكرر** (كان نسخة مطابقة في مجلد src).
- ✅ **البناء الإنتاجي ناجح**: `tsc && vite build` بدون أخطاء.

### 3. التحقق الشامل (تم فعلياً)
```
Backend tests:        96/96 passed ✅
Production build:     tsc + vite ✓ ✅
API Health:           /health/ → healthy ✅
Login (كلمة مرور):    admin@securemed.app → 200 ✅
Channels API:         5 قنوات ✅
Patients API:         8 مرضى ✅
Analytics API:        إحصائيات حقيقية ✅
Security Dashboard:   فحص ثغرات حي ✅
WAF:                  يحجب SQLi/XSS/Path Traversal ✅
UI (9 صفحات):        مصوّرة ومُتحقق منها بصرياً ✅
```

### حسابات الدخول
| الدور | البريد | كلمة المرور |
|------|--------|-------------|
| مدير النظام | admin@securemed.app | SecureMed@2026! |
| طبيب | doctor.ahmed@securemed.app | Doctor@2026! |
| ممرض | nurse.sara@securemed.app | Nurse@2026! |

---

# 🚀 Phase 4 — الحزمة الشاملة للمزايا المتقدمة (2026-08-30)

## المزايا الجديدة (10 مزايا — كلها مختبرة فعلياً)

### 1. دردشة القنوات الطبية 💬
- نموذج `ChannelMessage` + endpoints (GET/POST) على `/api/v1/channels/{id}/messages/`
- تحديث تلقائي كل 3 ثوانٍ (polling)، تمييز المرسل ودوره، سجل تدقيق `CHANNEL_MESSAGE_SENT`
- إصلاح إيجابية كاذبة ثانية في WAF: نمط SQL كان يحجب أي JSON قيمته تبدأ بمسافة — شدّد النمط ليتطلب كلمة SQL فعلية مع الحفاظ على كشف `' OR '1'='1`

### 2. ملف المريض الشامل 👤
- endpoint تجميعي `/api/v1/patients/{id}/profile/` (بيانات + سجلات + قنوات + ملفات + إحصاءات)
- صفحة `/patients/:id` بخط زمني للسجلات + بطاقات القنوات والملفات — محمية بالصلاحيات

### 3. البحث الشامل (Ctrl+K) 🔍
- endpoint `/api/v1/auth/search/?q=` يبحث في المرضى (فك تشفير PII في بايثون) والقنوات والمستخدمين — نتائج مقيدة بالصلاحيات
- نافذة بحث منبثقة (Ctrl+K / Cmd+K) مع debounce وتصنيف النتائج

### 4. الإشعارات الفورية للمتصفح 🔔
- Browser Notifications API: عند وصول إشعار جديد يظهر إشعار نظام قابل للنقر ينقل لمركز الإشعارات
- طلب الإذن عند أول إشعار + بديل toast عند الرفض

### 5. تقرير القناة PDF 📄
- `/api/v1/reports/channel/{id}/pdf/` — تقرير احترافي بالعربية (ReportLab + arabic-reshaper + bidi + DejaVu)
- يشمل: معلومات القناة، بيانات المريض (مفككة التشفير)، الأعضاء، السجلات، الملفات

### 6. تصدير التدقيق Excel 📊
- `/api/v1/reports/audit/excel/` — ملف xlsx بورقتين (السجل + ملخص) مع تنسيق وفلاتر
- متاح للمدير والمراجع الأمني فقط

### 7. التقرير الشهري 📈
- `/api/v1/reports/monthly/pdf/` — PDF برسوم matplotlib عربية (توزيع القنوات، النشاط اليومي، خطورة الأحداث) + مؤشرات KPI

### 8. المساعد الذكي (GLM) 🤖
- خدمة Node مستقلة `ai-service/` (منفذ 8100) عبر z-ai-web-dev-sdk
- الواجهة تستدعيها عبر proxy ‏`/ai` — ترسل سؤالاً + لقطة إحصائيات حية (مقيدة بالصلاحيات)
- يجيب بالعربية عن حالة المنصة — أرقام دقيقة من البيانات الحية (تم التحقق: 8 مرضى/5 قنوات/2 حرجة)

### 9. التحقق بخطوتين TOTP 🔐
- `pyotp` + QR: إعداد/تحقق/تعطيل + مسار دخول كامل (requires_2fa → mfa_token مؤقت بالكاش → 2fa/login)
- واجهة كاملة في الملف الشخصي + خطوة رمز في صفحة الدخول — أحداث تدقيق MFA_ENABLED/DISABLED/LOGIN

### 10. إدارة أجهزة البصمة 📱
- سيريالايزر صحيح لـ `BiometricProfileViewSet` + حذف نهائي `/remove/` + إصلاح صلاحية الكائن (كانت تقارن الجهاز بالمستخدم → 403 خاطئ)
- قائمة الأجهزة في الملف الشخصي مع حالة النشاط والحذف

## الاختبارات
- **20 اختبار جديد** في `test_phase4_features.py` (دردشة، بحث، 2FA، أجهزة، ملف مريض، تقارير)
- **116/116 اختبار ناجح** (96 الأصلية + 20) — صفر انحدارات
- بناء إنتاجي نظيف `tsc && vite build`

## التحقق الفعلي بالمتصفح (تم)
```
دخول بكلمة مرور → dashboard ✅
Ctrl+K بحث شامل → نتائج مصنفة → نقر → ملف مريض ✅
دردشة: إرسال رسالة عربية → ظهور فوري + polling ✅
زر تقرير PDF → تنزيل ملف حقيقي ✅
زر تصدير Excel → تنزيل xlsx ✅
زر التقرير الشهري → تنزيل PDF برسوم ✅
2FA: تفعيل → QR → تأكيد رمز → خروج → دخول بخطوة رمز → نجاح ✅
المساعد الذكي: سؤال → إجابة بدقة من البيانات الحية ✅
```

## تشغيل خدمة الذكاء الاصطناعي
```bash
cd ai-service && npm install && npm start   # منفذ 8100 (proxy ‏/ai في Vite)
```

---

# المرحلة الخامسة — التوسعة الوظيفية (AI Summaries + البريد + APK)

## 11. الملخص الذكي للحالة السريرية 🤖
- `ai-service`: نقطة نهاية جديدة `POST /case-summary` — برومبت سريري صارم يمنع اختراع أي معطى غير موجود في السجلات، ويُنظّم الملخص (نظرة عامة / نتائج سريرية / أدوية / نقاط انتباه / توصيات) + إخلاء مسؤولية إلزامي
- Backend: `POST /api/v1/patients/{id}/ai-summary/` — يجمع نفس بيانات `profile/` المرشّحة بالصلاحيات ثم يستدعي خدمة AI داخلياً (server-to-server، الخدمة لا تُكشف للخارج) — تدقيق AI_SUMMARY_GENERATED/FAILED
- الواجهة: بطاقة «الملخص الذكي» في ملف المريض مع توليد/إعادة توليد/نسخ + عرض Markdown عربي + ذكر عدد السجلات المبني عليها
- ملاحظة تقنية: `@action(url_path='ai-summary')` صراحةً (DRF لا يستبدل الشرطة السفلية تلقائياً هنا)

## 12. إشعارات البريد الإلكتروني 📧
- `backend/utils/email_service.py`: خدمة بريد مركزية بقالب HTML عربي RTL بهوية SecureMed (رأس متدرج، KPI tables، تذييل) — إرسال fail-safe لا يكسر الطلبات
- اختيار الخلفية تلقائياً: SMTP عند تعريف EMAIL_HOST (إنتاج) / ملفات .eml حقيقية في `backend/logs/emails/` للتطوير والعرض / console كاحتياط
- ربط حقيقي بـ `send_notification`: الإشعارات تُرسل فعلية الآن (كانت محاكاة) مع احترام تفضيلات المستخدم وساعات الهدوء — is_email_sent يعكس الواقع
- `POST /api/v1/notifications/test_email/` — رسالة اختبار للبريد من الواجهة (تدقيق TEST_EMAIL_SENT)
- بطاقة «إشعارات البريد الإلكتروني» في مركز الإشعارات: زر اختبار + زر إرسال التقرير الشهري (للمدراء/المراجعين)

## 13. التقارير المجدولة بالبريد 📅
- `apps/reports/monthly.py`: استخراج توليد التقرير الشهري إلى وحدة قابلة لإعادة الاستخدام (view + بريد + أمر مجدول = مصدر واحد للحقيقة) + `send_report_email` بمرفق PDF
- `POST /api/v1/reports/monthly/email/` (admin/auditor) — توليد + إرسال فوري لكل المدراء والمراجعين النشطين (تدقيق MONTHLY_REPORT_EMAILED)
- أمر الإدارة `send_scheduled_reports`:
  - `--type monthly`: تقرير PDF كامل بمرفق لكل المدراء/المراجعين
  - `--type weekly`: ملخص KPI أسبوعي (مرضى/قنوات/سجلات/رسائل/أحداث أمنية/حظر WAF) بقالب جدول أنيق
- جدولة cron مقترحة موثقة داخل الأمر (شهرية يوم 1 الساعة 8:00، أسبوعية الأحد)

## الاختبارات والتحقق
- **16 اختبار جديد** في `test_phase5_features.py` (ملخص AI مع محاكاة الخدمة، البريد عبر locmem، صلاحيات الإرسال، الأوامر المجدولة)
- **132/132 اختبار ناجح** (116 + 16) — صفر انحدارات
- بناء إنتاجي نظيف `tsc --noEmit && vite build`
- تحقق متصفح فعلي: توليد ملخص AI كامل من ملف مريض حقيقي (HbA1c/ميتفورمين من السجلات) + رسائل .eml فعلية بمرفق PDF في logs/emails/
- إصلاح: `EmailMessage` لا يدعم `attach_alternative` → `EmailMultiAlternatives`

## 14. تطبيق الأندرويد — بناء APK ناجح 📱
- تثبيت Android SDK (cmdline-tools + platform-34 + build-tools 34.0.0) + Gradle 8.8 + JDK 17 محمول (Temurin — JRE النظام بلا jlink)
- إصلاحات بناء ضرورية (كان الكود لا يُترجم أصلاً):
  * `converter-kotlinx-serialization` الإصدار الصحيح 2.11.0 (كان 1.0.0 غير موجود)
  * توليد أيقونات التطبيق (mipmap بجميع الكثافات — درع + صليب طبي، PIL) — كانت مفقودة تماماً
  * NotificationsScreen: فك `Result<List<>>` الصحيح (كان يمرر Result كقائمة → `it` غير محلول)
  * استيراد `background` المفقود في 3 شاشات + `clickable` + نقل استيراد طائش من نهاية DashboardScreen
  * `@OptIn(ExperimentalMaterial3Api::class)` لـ TopAppBar + اقتباسات عربية سليمة في ProfileScreen
  * تعارض `BiometricManager` (androidx مقابل com.securemed.app.auth) — إبقاء نسخة المشروع
  * proguard: `-dontwarn` لمعرّفات errorprone المرجعية من Tink
- بيئة محدودة الذاكرة: `-Xmx1536m` + workers.max=2 + kotlin in-process
- **النتيجة**: `SecureMed-v1.0.0-debug.apk` (19.2MB) + `SecureMed-v1.0.0-release.apk` (1.96MB بعد R8)
- تعديل `API_BASE_URL` من gradle property عند التشغيل على جهاز حقيقي (10.0.2.2 للمحاكي)

---

# المرحلة السادسة — الجاهزية للإنتاج والنشر المجاني ☁️

## الهدف
تحويل المنصة من «تعمل محلياً» إلى «قابلة للنشر بنقرة واحدة» — تمهيداً لبناء APK يشير إلى خادم حقيقي.

## 15. تحصين إعدادات الإنتاج (backend/config/settings.py)
- دعم `DATABASE_URL` سحابي (Neon/Render PostgreSQL) عبر dj-database-url مع `ssl_require` + ترتيب حل قاعدة البيانات: `file:` → sqlite / `postgres://` → سحابي / `DB_ENGINE=sqlite` → عرض / `DB_*` → postgres ذاتي
- شهادات mTLS للقاعدة أصبحت شرطية (`DB_SSL_CLIENT_CERTS=1`) بدل إلزامية — التوافق مع مزودي السحابة
- JWT: RS256 تلقائي عند وجود شهادات PEM، وإلا HS256 بمفتاح SECRET_KEY (لا مفاتيح خاصة في الصورة السحابية)
- `CSRF_TRUSTED_ORIGINS` يُشتق تلقائياً من ALLOWED_HOSTS مع دعم wildcard (`.onrender.com` → `https://*.onrender.com`)
- `SECURE_SSL_REDIRECT` / `SECURE_HSTS_SECONDS` قابلة للتجاوز بالبيئة
- كاش Redis اختياري عبر `REDIS_URL` (تعدد عمال) مع locmem افتراضياً
- ضمان وجود مجلدات logs/media عند الإقلاع (حاويات نظيفة)

## 16. خدمة SPA من Django — نشر الخدمة الواحدة
- `vite.config.ts`: base ديناميكي (`/static/` في الإنتاج، `/` في التطوير) — الأصول المُبصمة تُخدم عبر whitenoise
- تبديل التخزين إلى `CompressedStaticFilesStorage` (بدون manifest — لأن index.html يشير للأصول بنص حرفي)
- `config/urls.py`: SPA catch-all مع استثناءات صريحة (api/admin/static/media/health/ai) + `/media/` في الإنتاج + Cache-Control: no-cache لـ index.html
- إصلاح favicon مكسور: أيقونة SVG حقيقية (درع + صليب طبي بتدرج العلامة) في public/ تُعاد كتابتها تلقائياً
- بناء إنتاجي نظيف: index-BiF06K4c.js (863KB) + index-Bs26eBDf.css (36KB)

## 17. وكيل المساعد الذكي داخل Django (apps/ai)
- `POST /ai/ask/`: وكيل server-to-server إلى خدمة AI — نفس مسار الواجهة الأمامية في التطوير والإنتاج، الخدمة لا تُكشف للإنترنت إطلاقاً
- حواجز: JWT إلزامي + WAF + تقييد (2000 حرف للسؤال، 10 رسائل تاريخ مع تطهير، 500KB سياق، 413 عند التجاوز) + تدقيق AI_ASSISTANT_QUERY/FAILED
- `GET /ai/health/`: فحص توفر بلا كشف بيانات (AllowAny، يرجع unavailable بأمان)
- إصلاح معماري: في الإنتاج لا يوجد Vite proxy — الواجهة تخاطب Django (same-origin) ويحوّل هو بنفسه

## 18. حزمة النشر
- `render.yaml`: Blueprint لخدمتين (web + ai) بنقرة واحدة مع fromService لحقن عنوان AI تلقائياً
- `deploy/build.sh` + `deploy/start.sh`: migrate + collectstatic + بذر تجريبي idempotent + gunicorn (1 worker/8 threads/timeout 120)
- `ai-service/start.sh`: توليد `.z-ai-config` من متغيرات البيئة (ZAI_BASE_URL/ZAI_API_KEY) عند الإقلاع
- `Dockerfile` + `.dockerignore` كبديل حاويات، و`.env.example` موثق بالكامل، و`.gitignore` جذري
- `docs/DEPLOYMENT.md`: دليل عربي خطوة بخطوة (GitHub → Neon → Render → SMTP → APK)

## 19. التحقق
- **150/150 اختبار ناجح** (132 + 18 جديدة في test_phase6_deployment.py: الوكيل بصلاحيات/تطهير/حدود/تدقيق، SPA catch-all، مصفوفة حل قاعدة البيانات، اشتقاق CSRF)
- تحقق إنتاجي كامل محلياً (سكربت verify_production.sh — 13/13): gunicorn + DEBUG=0 → health/SPA مسارات عميقة/أصول static/دخول JWT/سؤال عربي حقيقي عبر وكيل AI بإجابة GLM فعلية/401 لغير المصادق/ترويسات أمان
- تدقيق مؤكد: AI_ASSISTANT_QUERY مسجل في AuditLog بقاعده البيانات
- مستودع git جاهز: commit أولي نظيف (221 ملف، بلا node_modules)

## حسابات التحقق
- admin@securemed.app / SecureMed@2026! (قاعدة التطوير المحلية)

---

# المرحلة 7: التطوير العميق الشامل — إغلاق كل الفجوات (Phase 7: Deep Completeness Pass)

## 1. الاستشار والتدقيق الشامل
- تدقيق كامل للمشروع: 150/150 اختبار أساس ناجح، الميزات الأولى (AI summaries، بريد وتقارير مجدولة، APK، جاهزية الإنتاج) مؤكدة من المراحل السابقة
- تحديد الفجوات المتبقية: **لا يوجد استعادة كلمة مرور** (فجوة حرجة)، API_BASE_URL ثابت في أندرويد، لا يوجد docker-compose، حزمة django_ratelimit غير مستخدمة تعطّل الإقلاع بلا Redis، سكربت البذر معطّل (مسار خاطئ)

## 2. ميزة استعادة كلمة المرور (Forgot Password) — كاملة من طرف لطرف
### Backend
- `POST /api/v1/auth/password/reset/` + `POST /api/v1/auth/password/reset/confirm/` (مجهولان + حد معدل 5/ساعة)
- رمز موقّع عبر Django `default_token_generator` (مرتبط بـ password hash + last_login → استخدام واحد تلقائي، صلاحية ساعة: `PASSWORD_RESET_TIMEOUT=3600`)
- ردّ موحّد دائماً (no user enumeration)، تدقيق `PASSWORD_RESET_REQUESTED/COMPLETED` في AuditLog، بريد عربي مُصمم (قوالب email_service) مع رابط `FRONTEND_URL`
- `PasswordResetRateThrottle` (AnonRateThrottle) في apps/security/throttling.py
- 11 اختبار جديد (tests/test_password_reset.py): التدفق الكامل، الاستخدام الواحد، الرفض (رمز/كلمة ضعيفة/عدم تطابق/uid مشوه)، عدم الحصيفرة

### Frontend
- صفحة `ForgotPassword.tsx` بمرحلتين: طلب الرابط (نموذج بريد → شاشة "افحص بريدك") + تعيين كلمة مرور جديدة (تلتقط uid/token من رابط البريد تلقائياً)
- مسار `/forgot-password` (عام) + رابط "نسيت كلمة المرور؟" في صفحة الدخول + دوال `requestPasswordReset/confirmPasswordReset` في authAPI
- بناء إنتاجي نظيف ✓

## 3. تحسينات البنية
- **إزالة django_ratelimit** من INSTALLED_APPS (حزمة غير مستخدمة إطلاقاً — الكود يستخدم DRF throttling + middleware مخصص): كانت ترفض الإقلاع عبر SystemCheckError E003 مع أي كاش بلا Redis
- **كاش FileBasedCache مشترك** كبديل locmem عند غياب REDIS_URL — صحيح لـ gunicorn متعدد العمال (throttling متماسك بين العمليات)
- **إصلاح سكربت البذر** scripts/seed_data.py (كان يضيف مجلد خاطئ إلى sys.path → ModuleNotFoundError)

## 4. Android: API_BASE_URL قابل للتكوين
- `android/app/build.gradle.kts`: قراءة `-PAPI_BASE_URL=...` مع fallback للمحاكي (10.0.2.2)
- `build_apk.sh`: معامل ثانٍ اختياري للرابط → `./build_apk.sh release https://<server>/api/v1/`
- جاهز لإعادة البناء فور اكتمال النشر الفعلي (بعد حصول المستخدم على عنوان عام)

## 5. Docker Compose كامل
- `docker-compose.yml`: backend (migrate+collectstatic+gunicorn) + ai-service + PostgreSQL اختياري (profile db) + healthchecks
- `ai-service/Dockerfile` جديد (node:20-alpine + healthcheck)
- `.env.example`: FRONTEND_URL + توثيق

## 6. التحقق النهائي
- **161/161 اختبار ناجح**
- **E2E حقيقي** (scripts/verify_password_reset.sh): طلب → بريد فعلي (.eml في logs/emails) → استخراج الرابط → تعيين كلمة مرور → دخول HTTP 200 → إعادة استخدام الرمز → 400
- **تحقق متصفح كامل** (agent-browser): صفحة الدخول → رابط "نسيت كلمة المرور؟" → نموذج البريد → شاشة "افحص بريدك" → فتح رابط الاستعادة → تعيين كلمة مرور → توجيه إلى /login → دخول API 200
- لقطات: screenshot_forgot_password.png، screenshot_reset_confirm.png

## الملفات المعدلة/الجديدة
- backend: settings.py، test_settings.py، accounts/{views,serializers,urls}.py، security/throttling.py، audit/models.py (+migration)، tests/test_password_reset.py، scripts/seed_data.py
- frontend: pages/ForgotPassword.tsx (جديد)، pages/Login.tsx، App.tsx، api/client.ts
- android: app/build.gradle.kts؛ الجذر: build_apk.sh، docker-compose.yml (جديد)، ai-service/Dockerfile (جديد)، .gitignore
- docs: TEST_RESULTS.md، DEVELOPMENT_LOG.md، README.md

---

# المرحلة 8: تدقيق متطلبات الخطة + نظام الأحواز + النسخ الاحتياطي (Phase 8: Plan Requirements Audit)

## 1. تدقيق متطلبات «plan 4 steps» (من صور المتطلبات)
| المتطلب | النتيجة |
|---|---|
| يتضمن أندرويد | ✅ موجود (Kotlin/Compose + BuildConfig) |
| ويب المكتب | ✅ موجود (React+Django) |
| إدارة مستخدمين | ✅ موجود + ترقية (تعديل/تفعيل/حوض) |
| حجم النظام مناسب | ✅ minify+shrink+gzip |
| الارتباط بالأحواز وتفعيلها بحسب النوع | ❌ كان غائباً ← **بُني بالكامل** |
| إشعارات وإنذارات | ✅ موجود (CRITICAL + SECURITY_ALERT + realtime) |
| الحماية من الهندسة العكسية | ✅ minifyEnabled + shrinkResources + ProGuard |
| واجهة الدخول + إدارة المستخدمين والصلاحيات | ✅ موجود (JWT+RBAC+صلاحيات القنوات) |
| تشفير البيانات الحساسة DB | ✅ حقيقي (AES-256/Fernet) |
| آلية النسخ الاحتياطي | ❌ كان غائباً ← **بُنيت بالكامل** |

## 2. تطبيق الأحواز الصحية (apps/basins) — جديد كلياً
### النموذج
- `Basin`: name/code فريدان، 7 أنواع (مستشفى عام/تخصصي/ريفي، مركز صحي، وحدة صحية، غسيل كلوي، عيادة تخصصية)، موقع (محافظة/مديرية)، مدير، طاقة استيعابية
- **محرك التفعيل بحسب النوع**: `DEFAULT_MODULES_BY_TYPE` — 8 وحدات قابلة للتفعيل (مرضى، قنوات، ملفات، مختبر، صيدلية، مساعد ذكي، تقارير، تحليلات)
- المستشفى العام = 8/8، المركز الصحي = 4، الوحدة الصحية = 2 (مرضى+قنوات فقط)
- `apply_default_modules()` تلقائي عند الإنشاء وتغيير النوع، + تفعيل/تعطيل يدوي فردي

### الربط (linkage)
- `User.basin` / `Patient.basin` / `Channel.basin` (PROTECT، مهاجرات 0003/0003/0004)
- القناة ترث الحوض تلقائياً من المالك أو المريض عند الإنشاء

### الإنفاذ الفعلي (ليس شكلياً)
- `ensure_module_enabled(user, module)` في: إنشاء المرضى، إنشاء القنوات، المساعد الذكي (/ai/ask) — PermissionDenied برسالة عربية واضحة تذكر نوع الحوض
- `basin_scoped_queryset()`: مدير المستشفى المربوط بحوض يرى مستخدمي/مرضى/قنوات حوضه فقط؛ SUPER_ADMIN يرى الكل
- حذف حوض مرتبط بمستخدمين ممنوع (403) — يُعطَّل بدلاً من ذلك

### API + واجهة
- `/api/v1/basins/`: CRUD (كتابة SUPER_ADMIN فقط) + `toggle_module` + `apply_type_defaults` + `my_basin` + `overview` + `modules` — كل الأحداث في AuditLog
- صفحة `Basins.tsx`: بطاقات الأحواز + شرائح الوحدات قابلة للنقر (أخضر=مفعّل) + زر «الافتراضي» لإعادة التفعيل حسب النوع + نموذج إنشاء/تعديل + إحصاءات لكل حوض
- Users.tsx: نماذج إنشاء/تعديل بحقل الحوض + زر تفعيل + تعديل الدور

## 3. آلية النسخ الاحتياطي (apps/backups) — جديدة كلياً
- **create_backup**: dumpdata (باستثناء الجداول العابرة: sessions + JWT blacklist) + manifest.json (بصمة SHA-256 + عدادات الجداول) + ملفات media/ → ZIP موحد + BackupRecord في DB
- **restore_backup <file> [--force]**: تحقق بصمة → flush (inhibit_post_migrate) → loaddata → استعادة الملفات؛ بدون --force = فحص سلامة فقط
- **استبقاء تلقائي**: آخر 14 نسخة (BACKUP_KEEP_COUNT)
- **API** (`/api/v1/backups/`, SUPER_ADMIN فقط): list + create_backup_action + download (FileResponse+audit) + verify + delete
- **أوامر إدارة**: `python manage.py create_backup --kind SCHEDULED` (للـ crontab) و `restore_backup`
- صفحة `Backups.tsx`: إنشاء فوري + جدول بالبصمات + فحص سلامة + تنزيل + حذف + تلميح أمر الاستعادة

## 4. التحقق
- **196/196 اختبار ناجح** (161 سابقة + 35 جديدة: 20 أحواز + 15 نسخ احتياطي — تشمل دورة إنشاء→عبث→كشف التلف→استعادة كاملة roundtrip)
- تحقق API حقيقي: أربعة أحواز مثبتة بأنواع مختلفة (8/8/4/2 وحدة)، إنشاء نسخة احتياطية 16.1KB ببصمة
- تحقق متصفح E2E: الأحواز (بطاقات + شرائح + إحصاءات) والنسخ الاحتياطي (جدول + إجراءات) والمستخدمون (عمود الحوض + أزرار التعديل/التفعيل) — لقطات verify_01..04
- بذر البيانات: 4 أحواز يمنية + ربط 10 مستخدمين و16 مريضاً و5 قنوات

## الملفات الجديدة
- backend/apps/basins/** (models/utils/views/serializers/urls/admin/migrations + 4 مهاجرات FK)
- backend/apps/backups/** (models/services/views/serializers/urls/admin/management commands + migration)
- backend/tests/{test_basins,test_backups}.py
- frontend/src/pages/{Basins,Backups}.tsx
