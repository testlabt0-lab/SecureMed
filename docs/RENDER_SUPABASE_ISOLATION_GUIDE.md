# دليل عزل وأمان الاتصال بين Render و Supabase (SecureMed Architecture)

يوضح هذا الدليل كيفية تطبيق **العزل الصارم (Network & Architectural Isolation)** بين خادم التطبيق المستضاف على **Render** وقاعدة البيانات المدارة على **Supabase**.

---

## 1. نموذج التهديد والهدف من العزل
- **خادم التطبيق (Render Web Service):** هو النقطة الوحيدة المسموح لها بالتخاطب المباشر مع قاعدة البيانات.
- **قاعدة البيانات (Supabase PostgreSQL):** يجب ألا تكون عرضة لأي وصول عشوائي من الإنترنت، ويجب إيقاف واجهات الـ REST API العامة إذا كان التطبيق يعتمد بالكامل على Django ORM.

---

## 2. خطوات العزل والتنفيذ

### أولاً: ضبط `DATABASE_URL` بريندر مع مجمع الاتصالات وتشفير TLS الإجباري
في لوحة تحكم Render -> Environment Variables:

1. **استخدام منفذ الـ Connection Pooler (منفذ 6543):**
   - لتفادي استنزاف الاتصالات (Connection Starvation) الناجم عن تشغيل عمال Daphne و Celery، استخدم عنوان الـ Pooler:
   ```env
   DATABASE_URL=postgres://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require
   ```
2. **إجبار تشفير TLS (`sslmode=require` أو `verify-full`):**
   - يضمن تشفير جميع البيانات الطبية وحركة الاستعلامات أثناء النقل (In-Transit Encryption) بين خوادم Render و Supabase.

---

### ثانياً: تقييد الوصول الشبكي (Supabase Network Restrictions)
1. افتح مشروعك في **Supabase Dashboard**.
2. انتقل إلى: **Project Settings** -> **Network**.
3. في قسم **Network Restrictions**:
   - بشكل افتراضي، تسمح Supabase بالاتصال من `0.0.0.0/0` (كل الإنترنت مع التوثيق).
   - إذا كنت تستخدم خطة Render مدفوعة (Team/Organization) مع **Static Outbound IP Addresses**، قم بإدخال عناوين IP الخاصة بـ Render هنا فقط لحظر أي اتصال خارجي آخر تماماً.
   - إذا كنت تستخدم الخطة المجانية، يتم الاعتماد على:
     1. التوثيق القوي بكلمة مرور معقدة عبر SCRAM-SHA-256.
     2. حظر هجمات القوة الغاشمة (Supabase Max Connection Bans).
     3. عزل مستويات الصلاحيات المطبقة في سكريبت `supabase_cis_level1_hardening.sql`.

---

### ثالثاً: قفل واجهة PostgREST / Supabase Public APIs
بما أن مشروع SecureMed يستخدم Django كباك إند رئيسي يدير الصلاحيات والمصادقة (JWT) وجلسات المرضى:
1. لا تعتمد على الـ Public API Keys الخاصة بـ Supabase (`anon` key) في الواجهة الأمامية.
2. سكريبت `supabase_cis_level1_hardening.sql` قام بالفعل بسحب جميع صلاحيات التعديل والقراءة التلقائية من دور `anon`.
3. لا تقم بتضمين `SUPABASE_URL` أو `SUPABASE_ANON_KEY` في متغيرات بيئة الـ Frontend (React). جميع الطلبات يجب أن تذهب حصراً إلى:
   ```
   https://securemed-production.onrender.com/api/v1/...
   ```

---

### رابعاً: عزل التخزين (Storage & Media Assets)
- ملفات الأشعة والتقارير الطبية المرفوعة تخزن إما عبر Supabase Storage بـ **Private Buckets فقط مع RLS**، أو عبر AWS S3 Bucket مشفر بـ SSE-S3 / KMS مع روابط موقّعة مؤقتة (Presigned URLs) تنتهي بعد 15 دقيقة.

---

## 3. قائمة التحقق الأمني (Render + Supabase Checklist)

| البند | الحالة الموصى بها | آلية التحقق |
| :--- | :---: | :--- |
| **تشفير الاتصال** | `sslmode=require` إلزامي | فحص استعلام `SELECT ssl_is_used();` |
| **مجمع الاتصالات** | Supavisor (Port 6543) | فحص المنفذ في `DATABASE_URL` |
| **تأمين المخطط العام** | `REVOKE CREATE ON SCHEMA public FROM PUBLIC` | تم تنفيذه عبر سكريبت التصليد |
| **تأمين الوصول المباشر** | RLS مفعل على 100% من الجداول | `SELECT * FROM vw_security_cis_audit_check;` |
| **حظر مفتاح Anon** | مسحوب من جميع الجداول | فحص `pg_roles` |
