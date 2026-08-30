# 🚀 دليل نشر SecureMed على استضافة مجانية

هذا الدليل ينشر المنصة كاملة **مجاناً**:

| المكوّن | الخدمة | العنوان النهائي |
|---------|--------|-----------------|
| Django API + واجهة React | Render (Web Service) | `https://securemed-web.onrender.com` |
| خدمة الذكاء الاصطناعي (GLM) | Render (Web Service) | `https://securemed-ai.onrender.com` |
| قاعدة البيانات PostgreSQL | Neon (خطة Free الدائمة) | سلسلة اتصال مشفّرة TLS |

> ⚠️ **مهم**: الخطة المجانية على Render «تنام» بعد 15 دقيقة بلا زيارات — أول طلب بعدها يستغرق ~50 ثانية للاستيقاظ. Neon مجانية للأبد (0.5GB) ولا تحتاج بطاقة.

---

## الخطوة 1 — ارفع المشروع إلى GitHub

```bash
cd securemed
git init
git add .
git commit -m "SecureMed v1.0 — production ready"
# أنشئ مستودعاً جديداً على github.com ثم:
git remote add origin https://github.com/<اسمك>/securemed.git
git branch -M main
git push -u origin main
```

> 💡 المشروع يحوي `frontend/dist` مبنياً مسبقاً — لا تحتاج Node على الخادم.

## الخطوة 2 — أنشئ قاعدة بيانات Neon

1. سجّل في <https://neon.tech> (أو GitHub).
2. أنشئ Project باسم `securemed`.
3. من لوحة المشروع انسخ **Connection string** (اختر *pooled connection*):
   ```
   postgresql://user:pass@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require
   ```
4. احتفظ به — ستحتاجه في الخطوة 3.

> المطلوب أمان قاعدة البيانات (متطلب #6) محقق: `sslmode=require` اتصال مشفّر إجباري.

## الخطوة 3 — انشر على Render (Blueprint بنقرة واحدة)

1. سجّل في <https://render.com> (أو GitHub).
2. **New +** ← **Blueprint** ← اختر مستودع `securemed`.
3. سيقرأ Render ملف `render.yaml` تلقائياً ويقترح خدمتين: `securemed-web` و `securemed-ai`.
4. قبل التطبيق املأ المتغيرات التي تظهر (نوع `sync`):
   - `DATABASE_URL` ← الصق سلسلة Neon من الخطوة 2.
   - `ZAI_BASE_URL` ← عنوان مزوّد GLM (مثال: `https://api.z.ai/v1`).
   - `ZAI_API_KEY` ← مفتاحك من منصة Z.ai.
   - (اختياري) `EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` لتفعيل بريد الإشعارات الحقيقي — مثال Gmail: `smtp.gmail.com` + App Password.
5. اضغط **Apply**. سيبنى كل شيء ويعمل خلال دقائق.

> ✅ الرابط بعد الانتهاء: `https://securemed-web.onrender.com` — افتحه وستعمل المنصة كاملة (واجهة + API + شاشة دخول).

## الخطوة 4 — تحقق من النشر

```bash
# فحص الصحة
curl https://securemed-web.onrender.com/health/

# فحص خدمة الذكاء الاصطناعي
curl https://securemed-ai.onrender.com/health

# دخول تجريبي
curl -X POST https://securemed-web.onrender.com/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@securemed.app","password":"Admin@2026!"}'
```

**حسابات العرض التجريبي** (تُبذر تلقائياً عند أول إقلاع — `SEED_DEMO_DATA=1`):

| الدور | البريد | كلمة المرور |
|-------|--------|-------------|
| مدير النظام | `admin@securemed.app` | `Admin@2026!` |
| طبيب | `doctor.ahmed@securemed.app` | `Doctor@2026!` |
| مراجع أمني | `auditor.ali@securemed.app` | `Audit@2026!` |

> 🔐 بعد أول دخول غيّر كلمات المرور، أو عطّل البذر (`SEED_DEMO_DATA=0`) وأنشئ حساباتك يدوياً.

## الخطوة 5 (اختيارية) — بريد حقيقي عبر Gmail

1. فعّل التحقق بخطوتين في حساب Google ثم أنشئ **App Password**.
2. في Render → خدمة `securemed-web` → **Environment**:
   ```
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_HOST_USER=you@gmail.com
   EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx
   ```
3. **Save** — الخدمة تعاد نشرها والبريد يعمل فوراً (إشعارات + تقارير شهرية مجدولة).

## الخطوة 6 (لاحقاً) — إعادة بناء APK ليشير إلى الرابط الحقيقي

بعد نجاح النشر، أعد بناء تطبيق أندرويد ليخاطب خادمك المنشور:

```bash
cd android
./gradlew assembleDebug -PAPI_BASE_URL=https://securemed-web.onrender.com
# أو للنسخة الموقعة:
./gradlew assembleRelease -PAPI_BASE_URL=https://securemed-web.onrender.com
```

---

## بديل: نشر يدوي (دون Blueprint)

إن فضّلت الإعداد اليدوي أنشئ خدمتين على Render:

**خدمة 1 — `securemed-web` (Python)**
- Root Directory: `backend`
- Build Command: `bash ../deploy/build.sh`
- Start Command: `bash ../deploy/start.sh`
- Health Check Path: `/health/`
- نفس متغيرات البيئة من `render.yaml`

**خدمة 2 — `securemed-ai` (Node)**
- Root Directory: `ai-service`
- Build Command: `npm install`
- Start Command: `bash start.sh`
- Health Check Path: `/health`
- ثم في خدمة الويب أضف: `AI_SERVICE_URL=https://securemed-ai.onrender.com`

## بديل: Docker

```bash
docker build -t securemed .
docker run -p 8000:8000 --env-file backend/.env securemed
```
يعمل على أي منصة تدعم الحاويات (Fly.io، أي VPS، إلخ).

---

## ملاحظات تشغيلية مهمة

1. **البريد في الوضع المجاني**: بدون `EMAIL_HOST` تُطبع الرسائل في سجل خدمة Render (Logs) — مناسب للعرض، ومع تعبئة متغيرات SMTP يعمل البريد الفعلي.
2. **التقارير المجدولة**: على الاستضافة المجانية لا يوجد cron خارجي؛ شغّل التقارير من الواجهة (بطاقة البريد ← «إرسال التقرير الشهري»)، أو اربط خدمة cron خارجية مجانية (مثل cron-job.org) لنقطة النهاية `POST /api/v1/reports/monthly/email/` مع توكن مدير، أو شغّل أمر الإدارة `python manage.py send_scheduled_reports --type monthly` عبر Render Cron Jobs (مدفوع) — الأول مجاني تماماً.
3. **الملفات المرفوعة (media)**: قرص الخطة المجانية مؤقت — الملفات المرفوعة تختفي مع إعادة النشر. للإنتاج الحقيقي اربط S3/R2.
4. **JWT**: يوقع HS256 بمفتاح `SECRET_KEY` تلقائياً (لا شهادات PEM في السحابة). لتوظيف RS256 على خادم ذاتي: ولّد الشهادات بـ `scripts/generate_certificates.py`.
5. **حدود المعدل**: تسجيل الدخول المجاني محمي بـ throttling (20 طلب/ساعة مجهول) — طبيعي أن ترى 429 عند الإجهاد المتكرر.
6. **تحديث النشر**: كل `git push` إلى `main` يعيد النشر تلقائياً (Auto-Deploy).

---

## 🗄️ النسخ الاحتياطي التلقائي (جديد — المرحلة 8)

المنصة تتضمن آلية نسخ احتياطي كاملة (قاعدة البيانات + الملفات المرفوعة) في أرشيف ZIP موثّق ببصمة SHA-256.

### يدوياً من الواجهة
`لوحة التحكم → النسخ الاحتياطي → «نسخة احتياطية الآن»` (متاح لمدير النظام فقط)

### سطر أوامر (للاستعادة أو الخوادم)
```bash
python manage.py create_backup --note "قبل التحديث"      # إنشاء نسخة
python manage.py restore_backup backups/<file.zip>        # فحص سلامة فقط
python manage.py restore_backup backups/<file.zip> --force  # استعادة فعلية
```

### جدولة يومية (crontab — كل يوم 2 فجراً)
```bash
0 2 * * * cd /path/to/backend && python manage.py create_backup --kind SCHEDULED >> logs/backup.log 2>&1
```

ملاحظات:
- يُحتفظ تلقائياً بآخر 14 نسخة (عدّل `BACKUP_KEEP_COUNT` في البيئة).
- مسار الحفظ: `BACKUP_DIR` (افتراضي `backend/backups/`) — أضِفه إلى نسخ النظام لديك.
- الاستعادة تتحقق من البصمة أولاً وترفض الأرشيف التالف أو المعدّل.
