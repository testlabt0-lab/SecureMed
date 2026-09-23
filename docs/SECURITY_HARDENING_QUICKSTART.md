# دليل التشغيل السريع: الحماية والامتثال (Security Hardening Quickstart)

يوفر هذا الدليل المرجع السريع لتشغيل واستخدام الأدوات الأمنية التي تم إضافتها إلى مشروع **SecureMed**.

---

## 1. فحص امتثال قاعدة البيانات لمعايير CIS (Supabase / PostgreSQL)

### تشغيل الفحص الآلي من سطر الأوامر:
يمكنك فحص قاعدة بياناتك الحالية والتأكد من مطابقتها للـ 15 نقطة Level 1 في أي وقت عبر أمر Django التالي:
```bash
python manage.py audit_cis_benchmark
```
يقوم الأمر بالاتصال بقاعدة البيانات وفحص:
- تشفير الاتصال (TLS/SSL).
- خوارزمية تشفير كلمات المرور (SCRAM-SHA-256).
- مهلات الجلسات الخاملة والاستعلامات (Timeouts).
- تفعيل RLS على 100% من الجداول.
- حظر الصلاحيات العامة من المخطط `public`.
- تفعيل وحالة إضافة `pgaudit`.

### تطبيق التصليد على Supabase:
إذا أظهر الفحص وجود نقاط ناقصة:
1. انسخ محتوى الملف: [`devsecops/scripts/supabase_cis_level1_hardening.sql`](file:///c:/Users/Essa/Downloads/securemed/devsecops/scripts/supabase_cis_level1_hardening.sql).
2. الصقه في **Supabase SQL Editor** واضغط **Run**.

---

## 2. التحقق من عزل خادم Render عن قاعدة بيانات Supabase
راجع الدليل الكامل في: [`docs/RENDER_SUPABASE_ISOLATION_GUIDE.md`](file:///c:/Users/Essa/Downloads/securemed/docs/RENDER_SUPABASE_ISOLATION_GUIDE.md).

تأكد من أن متغير البيئة في Render مضبوط على مجمع الاتصالات (Port 6543):
```env
DATABASE_URL=postgres://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require
```

---

## 3. اختبار حماية تطبيق الأندرويد ضد الهندسة العكسية

### بناء حزمة Release مشفرة ومطموسة الكود:
```bash
cd android
./gradlew assembleRelease
```
- يقوم محرك **R8** بحذف أسماء الدوال والكلاسات وأرقام الأسطر عبر الإعدادات في [`proguard-rules.pro`](file:///c:/Users/Essa/Downloads/securemed/android/app/proguard-rules.pro).
- يراقب كلاس [`TamperDetection.kt`](file:///c:/Users/Essa/Downloads/securemed/android/app/src/main/java/com/securemed/app/security/TamperDetection.kt) وقت التشغيل لمنع:
  - تشغيل التطبيق على بيئات Frida أو Xposed.
  - تشغيل التطبيق تحت تصحيح الأخطاء (Debugger Attached).
  - إعادة تجميع التطبيق وتوقيعه بمفاتيح غير أصلية (Signature Verification).

---

## 4. فحص الكود بواسطة SonarQube

### أ) الفحص المحلي الفوري عبر Docker:
- **في ويندوز:** انقر مرتين على الملف:
  [`devsecops/scripts/run_sonarqube_local.bat`](file:///c:/Users/Essa/Downloads/securemed/devsecops/scripts/run_sonarqube_local.bat)
- **أو عبر سطر الأوامر:**
  ```bash
  ./devsecops/scripts/run_sonarqube_local.sh
  ```
- سيفتح خادم SonarQube على `http://localhost:9000`.

### ب) الفحص الآلي في GitHub Actions:
- تم ربط الفحص في الملف: [`.github/workflows/sonarqube.yml`](file:///c:/Users/Essa/Downloads/securemed/.github/workflows/sonarqube.yml).
- لإتاحته على GitHub، أضف السريين التاليين في إعدادات المستودع (Settings -> Secrets and variables -> Actions):
  - `SONAR_TOKEN`: التوكن المستخرج من SonarQube أو SonarCloud.
  - `SONAR_HOST_URL`: عنوان الخادم (مثل `https://sonarcloud.io` أو رابط خادمك).
