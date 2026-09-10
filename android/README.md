# SecureMed Android

تطبيق الأندرويد لنظام SecureMed الطبي — Compose + Hilt + Retrofit + Room
(SQLCipher)، واجهته الخادمية Django على `/api/v1/`.

## متطلبات البناء

| الأداة | الإصدار |
|---|---|
| JDK | 17 (Temurin مُختبَر) — لا تستخدم JDK 21+ محلياً: detekt 1.23.x يرفض `--jvm-target` الأعلى من 21 (مثبَّت 17 في `app/build.gradle.kts` ويعمل على 17 في CI) |
| Android SDK | compileSdk 35، build-tools 35.0.0 |
| Gradle | 8.8 (عبر `gradlew`) |
| AGP / Kotlin | 8.6.1 / 1.9.24 |

```bash
# بناء تجريبي
./gradlew assembleDebug

# الاختبارات والتحليل الساكن
./gradlew testDebugUnitTest detekt
```

## عنوان الـ API

| النمط | الافتراضي | التجاوز |
|---|---|---|
| debug | `http://10.0.2.2:8000/api/v1/` (محاكي → الجهاز المضيف) | `-PAPI_BASE_URL=...` |
| release | `https://securemed-production.onrender.com/api/v1/` | `-PAPI_BASE_URL=...` |

قواعد هامة (انظر `app/build.gradle.kts`):

- عنوان الإنتاج **يجب** أن يكون HTTPS — loopback النصي يعطّل الـ
  certificate pinning في OkHttp ويسمح نصاً عبر `network_security_config`.
- التجاوز يمر للـ BuildConfig فقط؛ لا يوجد عنوان في شيفرة Kotlin.

## التوقيع

مادة المفتاح خارج المستودع تماماً — من `~/.gradle/gradle.properties`
أو من بيئة CI:

```properties
SECUREMED_KEYSTORE_FILE=/absolute/path/securemed-release.jks
SECUREMED_KEYSTORE_PASSWORD=...
SECUREMED_KEY_ALIAS=...
SECUREMED_KEY_PASSWORD=...
```

- بدونها، بناء release يطبع تحذيراً صريحاً وينتج AAB **غير موقَّع**
  (يفشل عند التثبيت — عن قصد، بدل توقيع debug الافتراضي الذي كان
  يُشحن سابقاً).
- v1 معطَّل عمداً (minSdk 26 لا يحتاجها وتوسّع سطح التلاعب)؛ v2+v3 مفعَّلة.

## توليد مخزن المفاتيح للمرة الأولى

```bash
keytool -genkeypair -v \
  -keystore securemed-release.jks -alias securemed \
  -keyalg RSA -keysize 4096 -validity 10000 \
  -storetype PKCS12
```

احفظ النسخة الاحتياطية خارج الأجهزة المتصلة — ضياعها بعد أول نشر يعني
عدم القدرة على تحديث التطبيق أبداً (Google Play لا يقبل مفتاحاً جديداً
إلا عبر Play App Signing).

## هاش توقيع التثبيت (شهادة التوقيع) وكيفية استخراجه

بصمة SHA-256 لشهادة توقيع الإصدار — هي ما يُسجَّل عند أي خدمات خادمية
تعتمد صحة التطبيق (Play Integrity لاحقاً، روابط deep-link الموقَّعة،
قوائم السماح الخادمية):

```bash
# من مخزن المفاتيح مباشرة:
keytool -list -v -keystore securemed-release.jks -alias securemed \
  | grep "SHA256:"

# أو من AAB/APK الموقَّع (الأدق — يقرأ ما نُشر فعلاً):
$ANDROID_HOME/build-tools/35.0.0/apksigner verify --print-certs app-release.aab
```

الخط المطلوب تسجيله بصيغته الشائعة:

```
AA:BB:CC:… (hex، نقطتان بين كل بايت، 32 بايت)
```

ملاحظة: بصمة توقيع debug تختلف عن release — أي تسجيل مُجرى لجلسة تجريبية
لا يصح للإنتاج.

## التحقق من هوية الجهاز (ليس هاش الشهادة)

الخادم يربط الجلسة بالجهاز عبر `X-Device-Fingerprint` — معرّف عشوائي
32-بايت يُولَّد مرة واحدة عند أول إقلاع ويُخزَّن محلياً
(`SecurePreferences.installId`)، لا `ANDROID_ID` ولا MAC. تغيّر IP أو
User-Agent يكسر ربط التوكن (JWT bound) ويُخرج الجلسة — هذا سلوك مقصود
موثَّق في `backend/apps/security/session_security.py`.

## خط الإصدار

```bash
git tag v1.0.0 && git push origin v1.0.0
```

وسم `v*` يشغّل `.github/workflows/android-release.yml`: detekt →
اختبارات الوحدة → AAB موقَّع (versionCode مشتق حسابياً من الوسم) →
تحقق `apksigner` → مرفق بـ GitHub Release. الأسرار المطلوبة في
المستودع: `ANDROID_KEYSTORE_BASE64`، `ANDROID_KEYSTORE_PASSWORD`،
`ANDROID_KEY_ALIAS`، `ANDROID_KEY_PASSWORD`.

قائمة ما قبل الرفع الأول (أذونات Play، إفصاح البيانات، حذف الحساب):
`docs/PLAY_STORE_CHECKLIST.md`.

## التخزين المحلي والخصوصية

- قاعدة Room **SQLCipher** (نسخة خادمية قابلة لإعادة الجلب + جداول
  خطط دوالّ جهازية) — باسفريسها في `SecurePreferences`؛ ضياعه يحذف
  القاعدة ويُعاد بناؤها (الخطط تهجر من JSON القديم مرة واحدة عند
  الإقلاع — بند 3-4).
- كاش القراءة دون اتصال AES-256-GCM بمفتاح hardware-backed.
- النسخ الاحتياطي للنظام: معطَّل بالكامل + قواعد
  `data_extraction_rules` تستثني كل شيء (PHI لا يغادر عبر قنوات
  النظام) — قائمة Play: `docs/PLAY_STORE_CHECKLIST.md`.

## شجرة المصادر (مختصر)

```
data/api/          Retrofit + اعتراضات الرؤوس والتجديد (NetworkModule)
data/local/        SecurePreferences، LocalCache (ترقية)، Room (data/local/room)
data/paging/       ترقيم الصفحات (PatientPagingSource، ApiPagingSource)
data/sync/         SyncWorker للأفعال المعلَّقة دون اتصال
reminders/         جدولة تنبيهات الدواء (AlarmManager) + استقبال الإقلاع
security/          AppLock، TamperDetection، SecureWipe، BiometricHelper
ui/screens/        شاشات Compose؛ نمط الحالة الموحَّد + LazyPagingItems
```

لخطة التطوير الكاملة والقرارات المسجَّلة: `../android/DEVELOPMENT_PLAN.md`،
وسجل الجلسات: `../docs/DEVELOPMENT_LOG.md`.
