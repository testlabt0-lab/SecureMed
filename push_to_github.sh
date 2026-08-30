#!/usr/bin/env bash
# =============================================================
#  SecureMed - رفع المشروع إلى GitHub باستخدام GitHub CLI
#  الاستخدام:
#     ./push_to_github.sh                 → مستودع باسم SecureMed (خاص)
#     ./push_to_github.sh MyName          → مستودع باسم مخصص (خاص)
#     ./push_to_github.sh MyName public   → مستودع باسم مخصص (عام)
# =============================================================
set -e

REPO_NAME="${1:-SecureMed}"
VISIBILITY="${2:-private}"

echo "=========================================="
echo "  SecureMed  ->  GitHub ($REPO_NAME, $VISIBILITY)"
echo "=========================================="

# 1) التحقق من الأدوات المطلوبة
command -v git >/dev/null 2>&1 || { echo "خطأ: Git غير مثبت - قم بتثبيته من https://git-scm.com"; exit 1; }
command -v gh  >/dev/null 2>&1 || { echo "خطأ: GitHub CLI غير مثبت - قم بتثبيته من https://cli.github.com"; exit 1; }

# 2) تسجيل الدخول إلى GitHub (مرة واحدة فقط)
if ! gh auth status >/dev/null 2>&1; then
  echo "يلزم تسجيل الدخول إلى GitHub أولاً..."
  gh auth login
fi

# 3) تهيئة Git داخل مجلد المشروع
git init 2>/dev/null || true
git branch -M main 2>/dev/null || true
git add .

if git diff --cached --quiet 2>/dev/null; then
  echo "لا توجد تغييرات جديدة (كل شيء مرفوع مسبقاً)"
else
  git commit -m "SecureMed: Django backend + React frontend + AI service + Android + docs"
fi

# 4) إنشاء المستودع على GitHub ورفع المشروع
if git remote get-url origin >/dev/null 2>&1; then
  echo "المستودع مرتبط مسبقاً، جاري التحديث..."
  git push -u origin main
  echo "تم التحديث: $(git remote get-url origin)"
else
  gh repo create "$REPO_NAME" --"$VISIBILITY" --source=. --remote=origin --push
  echo "=========================================="
  echo "اكتمل بنجاح! المستودع: https://github.com/$(gh api user -q .login)/$REPO_NAME"
  echo "=========================================="
fi
