# Security Policy — SecureMed

## الإبلاغ عن ثغرة

لا تفتح issue عاماً لثغرة أمنية. أرسل التفاصيل إلى فريق المشروع مباشرة مع:
وصف السيناريو، الخطوات لإعادة الإنتاج، والأثر المتوقع. الهدف: إصلاح خلال 7
أيام للثغرات الحرجة (تفويض/PHI)، و30 يوماً للبقية.

## الإصدارات المدعومة

| النسخة | مدعومة |
|---|---|
| main | نعم |
| أقدم | لا |

## الضوابط الأساسية (ملخص)

التفصيل الكامل في `docs/SECURITY_OVERVIEW.md` ونموذج التهديد في
`docs/THREAT_MODEL.md` والمصفوفة في `docs/SECURITY_TRACEABILITY.md`.

- عزل ثلاثي الطبقات: Basins → Channels → RBAC (11 دوراً)
- JWT (RS256/HS256 موثّق) بتدوير وقائمة حظر وربط جهاز
- TOTP + WebAuthn بتحقق تشفيري كامل على الخادم
- تشفير أعمدة PHI (Fernet + بادئة `v1:`) وتشفير ملفات (AES-256-GCM)
- /media/ بمصادقة وتفويض قناة وتدقيق قراءة
- سجل تدقيق HMAC مقفول، فحص تلقائي يومي، منع الحذف من الإدارة
- WAF + rate limiting + حظر أجهزة + توثيق أجهزة (حظر أو تحدي تكيفي)
- CI أمني حاجز: Bandit، Gitleaks، pip-audit، Trivy؛ SBOM لكل بيئة

## الإعدادات الإنتاجية الإلزامية

حرس `config/settings.py` يرفض الإقلاع إذا غابت هذه المتغيرات:

- `SECRET_KEY`، `ENCRYPTION_KEY` (غير الافتراضية)
- `AUDIT_LOG_HMAC_KEY` (مفتاح مستقل عن SECRET_KEY؛ الاستثناء بـ
  `AUDIT_LOG_ALLOW_SECRET_KEY_FALLBACK=1` فقط لنشر قائم)
- `REDIS_URL` أو `CACHE_BACKEND=django.core.cache.backends.db.DatabaseCache`
- `TELEGRAM_WEBHOOK_SECRET` إن كان توثيق الأجهزة عبر تيليجرام مفعلاً
