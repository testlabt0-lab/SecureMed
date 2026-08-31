# 🚀 دليل نشر SecureMed على Render + Neon — خطوة بخطوة

> دليل عملي كامل لنشر المنصة على البنية المجانية: **Render** (استضافة التطبيقات) + **Neon** (قاعدة بيانات PostgreSQL سحابية).
> اتبع الخطوات بالترتيب — تستغرق العملية كاملة من 15 إلى 25 دقيقة.

---

## 📐 المعمارية بعد النشر

| المكوّن | أين يستضيف | العنوان بعد النشر |
|---|---|---|
| Django API + واجهة React المبنية (خدمة واحدة) | Render — Web Service (Python) | `https://securemed-web.onrender.com` |
| المساعد الذكي AI (GLM) | Render — Web Service (Node) | `https://securemed-ai.onrender.com` |
| قاعدة بيانات PostgreSQL | **Neon** (مجاني دائم) | رابط `postgresql://...pooler...neon.tech/neondb?sslmode=require` |

- خدمة الويب تقدّم **كل شيء من نطاق واحد**: الـ API على `/api/v1/*`، المساعد عبر وكيل `/ai/*`، وواجهة React المبنية (SPA) من الجذر `/` — لذلك **لا توجد مشاكل CORS أصلاً**.
- عند أول إقلاع يتم تلقائياً: إنشاء الجداول (`migrate`) ثم زرع بيانات تجريبية (مستخدمون + مرضى + قنوات + سجلات).

---

## ✅ المتطلبات المسبقة

1. **المشروع مرفوع على GitHub** (خاص أو عام — كلاهما يعمل).
   - إذا لم ترفعه بعد: اتبع `GITHUB_GUIDE.md` أو شغّل `bash push_to_github.sh` من جهازك.
2. حساب **GitHub** نشط.
3. لا تحتاج بطاقة بنكية — Render وNeon يقدمان خططاً مجانية دائمة.

> ⚠️ مهم جداً قبل الرفع: تأكد أن مجلد `frontend/dist/` **مرفوع داخل المستودع** (وليس مستثنياً في `.gitignore`)، لأن خدمة Render تقدّم الواجهة منه مباشرة دون بناء Node على الخادم. النسخة الحالية من المشروع تتضمنه.

---

## الخطوة 1 — إنشاء قاعدة البيانات على Neon (5 دقائق)

1. افتح **https://neon.tech** واضغط **Sign Up** ثم سجّل بحساب GitHub (الأسهل) أو Google.
2. بعد الدخول اضغط **Create project** (أو "Create your first project"):
   - **Project name**: `securemed`
   - **PostgreSQL version**: اترك الافتراضي (17)
   - **Cloud region**: اختر الأقرب لمنطقتك — للأخوان في اليمن/الخليج: `EU Central (Frankfurt)` أو `AWS Bahrain (me-central-1)` إن ظهرت
3. اضغط **Create**.
4. ستظهر شاشة **Connect to your database** (أو زر **Connect** في الشريط العلوي):
   - اختر تبويب **Connection string** أو **Pooled connection** ← ⚠️ **اختر "Pooled" حتماً** (لاحظ أن الرابط يحتوي `-pooler` في اسم المضيف — هذا ضروري لسعة الاتصالات في الخطة المجانية).
5. انسخ الرابط كاملاً، سيكون بهذا الشكل:

```
postgresql://neondb_owner:AbCd1234xYz@ep-cool-darkness-a1b2c3d4-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require
```

6. احفظه في مكان آمن مؤقتاً (سنلصقه في Render بعد قليل). **لا تشاركه مع أحد** — الرابط يحتوي كلمة المرور.

> 💡 ملاحظات على Neon المجاني:
> - السعة 0.5 GB — تكفي آلاف المرضى والسجلات للتجربة والاستخدام الصغير.
> - القاعدة "تنام" بعد ~5 دقائق خمول (autosuspend)؛ أول استعلام بعدها يأخذ أقل من ثانية إضافية — طبيعي تماماً.

---

## الخطوة 2 — الدخول إلى Render وربط GitHub (3 دقائق)

1. افتح **https://render.com** واضغط **Get Started for Free** ثم **GitHub**.
2. اسمح لـ Render بالوصول:
   - اضغط **Configure** في شاشة تفويض GitHub، ثم اختر **All repositories** (الأسهل) أو **Only select repositories** واختر مستودع `securemed`.
3. اضغط **Install** → سيحوّلك إلى لوحة تحكم Render.

---

## الخطوة 3 — النشر بالـ Blueprint (الطريقة الأسهل — كل شيء تلقائي)

المشروع يحتوي ملف `render.yaml` جاهزاً يعرّف الخدمتين بكل إعداداتهما.

1. في لوحة Render اضغط **New +** من الأعلى → اختر **Blueprint**.
2. اختر المستودع `securemed` من القائمة واضغط **Connect**.
3. سيقرأ Render الملف تلقائياً ويعرض الخدمتين:
   - `securemed-web` (Python)
   - `securemed-ai` (Node)
4. قبل الإنشاء سيطلب منك تعبئة المتغيرات الفارغة (`sync: false`) — املأها هكذا:

| المتغير | القيمة | إلزامي؟ |
|---|---|---|
| `DATABASE_URL` | **الصق رابط Neon** الذي نسخته في الخطوة 1 | ✅ نعم — بدونها ستعمل بخادم SQLite مؤقت |
| `ZAI_BASE_URL` | مثل `https://api.z.ai/v1` | اختياري — للمساعد الذكي |
| `ZAI_API_KEY` | مفتاحك من منصة Z.ai | اختياري — للمساعد الذكي |
| `EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | بيانات SMTP (مثل Gmail بكلمة تطبيق) | اختياري — لرسائل البريد الحقيقية |

> ✨ المتغيرات المولّدة تلقائياً (`SECRET_KEY`, `ENCRYPTION_KEY`) و`AI_SERVICE_HOST` سيتولى Render إنشاؤها وربطها بنفسه.

5. اضغط **Apply** / **Deploy Blueprint**.
6. انتظر 5–10 دقائق — راجع سجل البناء (Logs) مباشرة. عند الانتهاء سترى الخدمتين بحالة **Live**.
7. أول إقلاع سينفّذ تلقائياً: `migrate` ثم زرع البيانات التجريبية ثم تشغيل gunicorn.

---

## الخطوة 3 (بديلة) — النشر اليدوي خدمةً خدمة

إذا فضّلت التحكم اليدوي بدل الـ Blueprint:

### أ) خدمة الويب (Django + الواجهة)

| الحقل | القيمة |
|---|---|
| New + → | **Web Service** → اختر المستودع |
| Name | `securemed-web` |
| Language / Runtime | **Python 3** |
| Branch | `main` |
| Root Directory | `backend` |
| Build Command | `bash ../deploy/build.sh` |
| Start Command | `bash ../deploy/start.sh` |
| Instance Type | **Free** |
| Health Check Path | `/health/` |

ثم من **Environment** أضف متغيرات البيئة (الجدول الكامل أدناه) — أهمها `DATABASE_URL` (رابط Neon) — ثم اضغط **Save and Deploy**.

### ب) خدمة المساعد الذكي (Node)

| الحقل | القيمة |
|---|---|
| New + → | **Web Service** → نفس المستودع |
| Name | `securemed-ai` |
| Language / Runtime | **Node** |
| Root Directory | `ai-service` |
| Build Command | `npm install` |
| Start Command | `bash start.sh` |
| Instance Type | **Free** |
| Health Check Path | `/health` |

مع متغيري البيئة `ZAI_BASE_URL` و`ZAI_API_KEY` (اختياريان).

### ج) الربط بينهما

في خدمة `securemed-web` → **Environment** أضف:

```
AI_SERVICE_URL = https://securemed-ai.onrender.com
```

ثم **Manual Deploy → Deploy latest commit** مرة واحدة لتفعيل القيمة.

---

## 🔐 جدول متغيرات البيئة الكامل (خدمة الويب)

| المتغير | القيمة على Render | ملاحظة |
|---|---|---|
| `PYTHON_VERSION` | `3.12.7` | ✅ موجودة في render.yaml — **لا تحذفها** (بدونها يفشل بناء psycopg2/matplotlib على Python 3.13) |
| `DJANGO_SETTINGS_MODULE` | `config.settings` | تلقائية |
| `SECRET_KEY` | مولّد تلقائياً (generateValue) | لا تعدّله |
| `ENCRYPTION_KEY` | مولّد تلقائياً (generateValue) | تشفير حقول المرضى AES-256 |
| `DEBUG` | `0` | |
| `ALLOWED_HOSTS` | `.onrender.com,localhost,127.0.0.1` | أضف دومينك المخصص لاحقاً بفاصلة |
| `CSRF_TRUSTED_ORIGINS` | `https://*.onrender.com` | يُشتق تلقائياً إن حُذف |
| `SECURE_SSL_REDIRECT` | `1` | فرض HTTPS |
| `DATABASE_URL` | رابط **Neon Pooled** | ⚠️ الأهم |
| `SEED_DEMO_DATA` | `1` | اجعلها `0` بعد أول إقلاع إذا لا تريد البيانات التجريبية |
| `AI_SERVICE_HOST` | يُربط تلقائياً من خدمة securemed-ai (Blueprint) | في النشر اليدوي: استخدم `AI_SERVICE_URL` |
| `FRONTEND_URL` | يُستنتج تلقائياً من `RENDER_EXTERNAL_URL` | روابط استعادة كلمة المرور |
| `EMAIL_HOST` + المستخدم + كلمة المرور | اختيارية | بدونها تُطبع الرسائل في السجلات (console) |

---

## الخطوة 4 — التحقق بعد النشر (قائمة فحص)

افتح في المتصفح بالترتيب (استبدل `securemed-web` باسم خدمتك الفعلي إن غيّرته):

| # | الرابط | النتيجة المتوقعة |
|---|---|---|
| 1 | `https://securemed-web.onrender.com/health/` | `{"status": "healthy", ...}` |
| 2 | `https://securemed-web.onrender.com/` | صفحة تسجيل دخول SecureMed (الواجهة تعمل) |
| 3 | تسجيل الدخول بـ `admin@securemed.app` / `Admin@2026!` | لوحة التحكم الرئيسية بإحصائيات حية |
| 4 | صفحة المرضى + فتح مريض | بيانات المرضى المزروعة |
| 5 | زر **تقرير PDF** من ملف مريض | تنزيل ملف PDF عربي سليم |
| 6 | المساعد الذكي (أيقونة الدردشة) | يجيب بالعربية (إن أدخلت مفاتيح ZAI) |
| 7 | `https://securemed-web.onrender.com/admin/` | لوحة Django الإدارية |

> ⏱️ تذكير مهم (الخطة المجانية): الخدمة "تنام" بعد 15 دقيقة بلا زيارات، وأول طلب بعدها ينتظر **50–60 ثانية** حتى تستيقظ. افتح الرابط وانتظر ثم أعد التحديث — هذا طبيعي في Free tier.

---

## 👥 بيانات الدخول التجريبية (تُزرع تلقائياً عند أول إقلاع)

| الدور | البريد | كلمة المرور |
|---|---|---|
| مدير النظام | `admin@securemed.app` | `Admin@2026!` |
| طبيب | `doctor.ahmed@securemed.app` | `Doctor@2026!` |
| ممرضة | `nurse.sara@securemed.app` | `Nurse@2026!` |
| مختبر | `lab.khalid@securemed.app` | `Lab@2026!` |
| مراجع أمني | `auditor.ali@securemed.app` | `Audit@2026!` |

> 🔒 **أمان**: غيّر كلمة مرور المدير فوراً بعد أول دخول (الملف الشخصي → تغيير كلمة المرور)، أو اجعل `SEED_DEMO_DATA=0` بعد أول إقلاع ثم أنشئ حسابك من `/admin/`.

---

## 🔄 كل تحديث مستقبلي = سطر واحد

أي `git push` إلى `main` على GitHub → **Render ينشر تلقائياً** (Auto-Deploy مفعّل افتراضياً):

```bash
git add -A
git commit -m "تحديث"
git push
```

مراقبة النشر: لوحة Render → الخدمة → **Events/Logs**. ويمكن إعادة النشر يدوياً بـ **Manual Deploy → Deploy latest commit**.

---

## ⚠️ حدود الخطة المجانية (مهم تعرفها)

| البند | الحد | الأثر العملي |
|---|---|---|
| Render Web Service | ينام بعد 15 دقيقة خمول | أول طلب يستغرق ~50 ثانية |
| ساعات التشغيل | 750 ساعة/شهر لكل حساب | تكفي خدمتين دائماً تقريباً |
| Neon | 0.5 GB تخزين + autosuspend 5 دقائق | تكفي التجربة والاستخدام الصغير |
| **الملفات المرفوعة (صور/مرفقات المرضى)** | **تُمسح عند إعادة النشر** (قرص مؤقت) | المرفقات المهمة: فعّل لاحقاً Render Disk (مدفوع) أو S3/Cloudinary |
| النسخ الاحتياطي | يعمل بـ dumpdata داخلياً | حمّل نسخة دورياً من صفحة النسخ الاحتياطي في المنصة |

---

## 🛠️ حل المشاكل الشائعة

| المشكلة في السجل/المتصفح | السبب | الحل |
|---|---|---|
| **`Exited with status 1 while building your code`** (فشل أول نشر) | السبب الأشهر: Render بنى الكود بـ **Python 3.13 الافتراضي** بينما الحزم القديمة (psycopg2 2.9.9 وغيرها) لا تملك نسخاً جاهزة له → يفشل `pip install`. أو أن Root Directory / Build Command غير مضبوطة في النشر اليدوي | **الحل السريع (دقيقتان، بدون رفع كود):** لوحة الخدمة → **Environment** → Add Environment Variable → الاسم `PYTHON_VERSION` والقيمة `3.12.7` → Save → **Manual Deploy → Deploy latest commit**. وإن كنت تنشر يدوياً: تأكد أن Root Directory = `backend` وأن Build Command = `bash ../deploy/build.sh`. **الحل الجذري:** ارفع نسخة v7 من المشروع (متطلبات محدثة تصمد على أي إصدار Python) ثم أعد النشر |
| فشل البناء في `pip install` (خطأ psycopg2) | Python 3.13 الافتراضي لا يوجد له wheels | تأكد من وجود `PYTHON_VERSION=3.12.7` في Environment |
| `Application error` / فشل Health Check | `DATABASE_URL` خاطئة أو migrate فشل | افتح Logs → صحّح رابط Neon (لا تنسَ `?sslmode=require`) → Manual Deploy |
| `DisallowedHost` | الدومين غير مسموح | أضفه إلى `ALLOWED_HOSTS` (مثل `.onrender.com`) |
| خطأ CSRF عند تسجيل الدخول | الأصل غير موثوق | `CSRF_TRUSTED_ORIGINS=https://*.onrender.com` |
| `502 Bad Request` فجأة | الخدمة نائمة (free tier) | انتظر دقيقة وأعد التحديث |
| `relation "..." does not exist` | migrate لم يُنفّذ | Logs → Manual Deploy (الإقلاع ينفّذ migrate تلقائياً) |
| صفحة الواجهة تعمل لكن `/api` يرجع HTML | طلب وصل للـ SPA بدل الـ API | تأكد أن الطلبات على `/api/v1/...` وأن Root Directory = `backend` |
| المساعد الذكي يرجع خطأ | مفاتيح ZAI ناقصة أو الخدمة نائمة | أدخل `ZAI_BASE_URL`/`ZAI_API_KEY`، وأعد المحاولة (أول محاولة توقظ الخدمة) |
| رسائل البريد لا تصل | لا يوجد SMTP | أضف `EMAIL_HOST` + مستخدم + كلمة مرور تطبيق (Gmail) |
| قاعدة Neon ترفض الاتصال | رابط Direct بدل Pooled | استخدم رابط **Pooled** (يحتوي `-pooler`) |

**أين تجد السجلات؟** لوحة Render → اضغط على الخدمة → تبويب **Logs** (يظهر فيه كل شيء: البناء، migrate، الأخطاء).

---

## 📱 الخطوة التالية: تطبيق Android

بعد نجاح النشر، عنوان الـ API الجاهز لتطبيق الأندرويد هو:

```
https://securemed-web.onrender.com
```

احفظ هذا الرابط — سنستخدمه في `build_apk.sh` لبناء APK يشير إلى خادمك المنشور.

---

## 📎 ملاحظات ختامية

- **دومين مخصص لاحقاً؟** اربطه من Render → Settings → Custom Domains، ثم أضفه إلى `ALLOWED_HOSTS` و`CSRF_TRUSTED_ORIGINS` وأعد النشر.
- كل شيء في هذا الدليل مطابق للملفات الموجودة فعلاً في المشروع: `render.yaml` + `deploy/build.sh` + `deploy/start.sh` + `ai-service/start.sh` — جرّبتُها محلياً محاكاةً لبيئة Render قبل كتابة الدليل (بناء ثابت + migrate + seed + gunicorn + فحص كل المسارات + 196 اختباراً ناجحاً).
