# 📤 دليل رفع مشروع SecureMed إلى GitHub باستخدام GitHub CLI

هذا الدليل يشرح خطوة بخطوة كيفية إنشاء مستودع جديد على GitHub ورفع المشروع إليه من جهازك مباشرة.

---

## الخطوة 1: تثبيت الأدوات المطلوبة

### أ) Git (إذا لم يكن مثبتاً)
| النظام | طريقة التثبيت |
|--------|----------------|
| Windows | من https://git-scm.com/download/win (أو `winget install Git.Git`) |
| macOS | `brew install git` |
| Linux | `sudo apt install git` |

### ب) GitHub CLI
| النظام | طريقة التثبيت |
|--------|----------------|
| Windows | `winget install GitHub.cli` |
| macOS | `brew install gh` |
| Linux | `sudo apt install gh` |

تحقق من نجاح التثبيت:
```bash
git --version
gh --version
```

---

## الخطوة 2: تسجيل الدخول إلى GitHub (مرة واحدة فقط)

افتح الطرفية (Terminal / CMD / PowerShell) واكتب:

```bash
gh auth login
```

ستظهر لك أسئلة، أجب كما يلي:
1. **What account do you want to log into?** → `GitHub.com`
2. **What is your preferred protocol?** → `HTTPS`
3. **Authenticate Git with your GitHub credentials?** → `Yes`
4. **How would you like to authenticate?** → `Login with a web browser`
5. انسخ الرمز الظاهر (مثل `ABCD-1234`) ثم اضغط Enter
6. سيفتح المتصفح → الصق الرمز → اضغط **Authorize**

التحقق من نجاح الدخول:
```bash
gh auth status
```

---

## الخطوة 3: رفع المشروع (الطريقة الآلية - الأسهل)

1. فك ضغط الملف `SecureMed_Complete_Project_v3.zip`
2. افتح الطرفية داخل مجلد المشروع:

**Windows:**
```cmd
cd C:\المسار\إلى\securemed
push_to_github.bat
```

**Linux / macOS / Git Bash:**
```bash
cd /المسار/إلى/securemed
chmod +x push_to_github.sh
./push_to_github.sh
```

أو حدد اسماً مخصصاً للمستودع:
```bash
./push_to_github.sh SecureMed-Platform        # مستودع خاص (موصى به)
./push_to_github.sh SecureMed-Platform public # مستودع عام
```

السكربت سينفذ تلقائياً: تهيئة Git ← إنشاء أول Commit ← إنشاء المستودع على GitHub ← الرفع.

في النهاية ستحصل على رابط مثل:
```
https://github.com/اسم-حسابك/SecureMed
```

---

## الخطوة 3 (بديلة): رفع المشروع (الطريقة اليدوية خطوة بخطوة)

إذا فضلت التنفيذ يدوياً بدلاً من السكربت:

```bash
# 1) انتقل إلى مجلد المشروع
cd securemed

# 2) تهيئة مستودع Git محلي
git init
git branch -M main

# 3) إضافة كل الملفات وإنشاء أول Commit
git add .
git commit -m "SecureMed: Django backend + React frontend + AI service + Android + docs"

# 4) إنشاء المستودع على GitHub ورفع المشروع بأمر واحد
gh repo create SecureMed --private --source=. --remote=origin --push
```

> 💡 `--private` = مستودع خاص (موصى به لمنصة أمنية)، استبدلها بـ `--public` إذا أردته عاماً.
> 💡 أمر `gh repo create` واحد يفعل ثلاثة أشياء: ينشئ المستودع على GitHub + يربطه بمجلدك (remote) + يرفع الكود (push).

---

## ما الذي سيُرفع وما الذي لن يُرفع؟

ملف `.gitignore` جاهز ومُعد مسبقاً، لذلك **لن تُرفع** الملفات التالية (وهذا مقصود وآمن):
- ❌ `node_modules/` — مكتبات الواجهة (تُعاد تثبيتها بـ `npm install`)
- ❌ `db.sqlite3` — قاعدة البيانات المحلية
- ❌ `.env` — ملفات المتغيرات السرية (المفاتيح)
- ❌ ملفات بناء Android الكبيرة (`android/app/build/`, `*.apk`)
- ❌ ملفات ZIP والنسخ المضغوطة

بينما **سيُرفع** كامل الكود المصدري: Django + React + AI Service + Android + التوثيق + سكربتات النشر.

> 🔒 ملاحظة أمنية: تم التحقق من أن `SECRET_KEY` يُقرأ من متغيرات البيئة وليس مكتوباً في الكود، فرفع المستودع حتى لو كان **عاماً** آمن من هذه الناحية — لكن يبقى المستودع الخاص هو الخيار الأنسب.

---

## الخطوة 4: تحديث المشروع لاحقاً (بعد أي تعديل)

```bash
git add .
git commit -m "وصف التعديل الذي قمت به"
git push
```

---

## خطوات مفيدة إضافية

**استنساخ المشروع على جهاز آخر:**
```bash
gh repo clone اسم-حسابك/SecureMed
```

**عرض حالة المستودع:**
```bash
git status          # الملفات المعدلة
git log --oneline   # سجل الـ Commits
gh repo view --web  # فتح المستودع في المتصفح
```

**إضافة وصف وقائمة مواضيع للمستودع:**
```bash
gh repo edit --description "SecureMed - Medical Safety & Adverse Reaction Reporting Platform"
gh repo edit --add-topic django,react,healthcare,security,hipaa
```

---

## حل المشاكل الشائعة

| المشكلة | الحل |
|---------|------|
| `gh: command not found` | أعد تشغيل الطرفية بعد التثبيت، أو أعد تثبيت GitHub CLI |
| `git: command not found` | ثبّت Git من git-scm.com وأعد تشغيل الطرفية |
| فشل الرفع `rejected` | نفّذ `git pull --rebase origin main` ثم `git push` |
| طلب اسم مستخدم وكلمة مرور عند الـ push | نفّذ `gh auth login` مجدداً وفعّل `gh auth setup-git` |
| خطأ `remote origin already exists` | المستودع مرتبط مسبقاً — نفّذ `git push -u origin main` فقط |
