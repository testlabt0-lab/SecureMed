"""
إدارة الصلاحيات الديناميكية — Dynamic role-based permissions.

المشكلة التي تحلها: الأدوار كانت قائمة ثابتة (TextChoices) مع صنف DRF لكل
دور؛ تعديل ما يستطيعه "ممرض" مثلاً يتطلب تعديل كود. هذا الملف يعرّف كتالوج
صلاحيات موحداً + الوضع الافتراضي لكل دور، وموديل ``RolePermission`` يسمح
للإدارة بتجاوز الافتراضي صلاحية-بصلاحية من الواجهة دون نشر كود جديد.

القاعدة: SUPER_ADMIN يملك كل شيء دائماً (لا يمكن قيده — حماية من إغلاق
الإدارة لنفسها)، وأي صلاحية لها تجاوز في RolePermission تطبق فوراً، وإلا
يسري الافتراضي أدناه.
"""

# (code, label_ar, category_ar) — الكود مستقر في قاعدة البيانات، فلا تعيد
# تسمية كود موجود؛ أضف واحداً جديداً بدلاً من ذلك.
PERMISSION_CATALOG = [
    ('patients.view', 'عرض المرضى', 'المرضى'),
    ('patients.create', 'إضافة مريض', 'المرضى'),
    ('patients.edit', 'تعديل بيانات مريض', 'المرضى'),
    ('patients.delete', 'حذف مريض', 'المرضى'),
    ('records.view', 'عرض السجلات الطبية', 'السجلات الطبية'),
    ('records.create', 'إنشاء سجل طبي', 'السجلات الطبية'),
    ('records.edit', 'تعديل سجل طبي', 'السجلات الطبية'),
    ('records.delete', 'حذف سجل طبي', 'السجلات الطبية'),
    ('appointments.view', 'عرض المواعيد', 'المواعيد'),
    ('appointments.manage', 'إدارة المواعيد', 'المواعيد'),
    ('prescriptions.manage', 'إدارة الوصفات الطبية', 'الوصفات والصيدلية'),
    ('pharmacy.manage', 'إدارة الصيدلية والمخزون', 'الوصفات والصيدلية'),
    ('billing.view', 'عرض الفواتير', 'الفوترة'),
    ('billing.manage', 'إدارة الفوترة والسداد', 'الفوترة'),
    ('channels.use', 'استخدام قنوات التواصل', 'القنوات'),
    ('channels.manage', 'إدارة القنوات والأعضاء', 'القنوات'),
    ('ai.use', 'استخدام المساعد الذكي', 'الذكاء الاصطناعي'),
    ('reports.view', 'عرض التقارير والإحصاءات', 'التقارير'),
    ('users.view', 'عرض المستخدمين', 'الإدارة'),
    ('users.manage', 'إدارة المستخدمين والأدوار', 'الإدارة'),
    ('permissions.manage', 'إدارة صلاحيات الأدوار', 'الإدارة'),
    ('basins.manage', 'إدارة الأحواض الصحية', 'الإدارة'),
    ('devices.manage', 'إدارة الأجهزة والتراخيص', 'الأمان'),
    ('security.manage', 'إدارة الأمان والحواجز', 'الأمان'),
    ('audit.view', 'عرض سجل التدقيق', 'الأمان'),
    ('backups.manage', 'إدارة النسخ الاحتياطي', 'الأمان'),
]

# اختصارات مريحة
_PERMISSIONS_BY_CODE = {code: (label, category) for code, label, category in PERMISSION_CATALOG}
ALL_PERMISSION_CODES = [code for code, _, _ in PERMISSION_CATALOG]

# الوضع الافتراضي لكل دور — يطبق ما لم يوجد تجاوز في RolePermission.
# الأدوار الغائبة هنا لا صلاحيات لها افتراضياً (الأكثر أماناً).
DEFAULT_ROLE_PERMISSIONS = {
    'HOSPITAL_ADMIN': ALL_PERMISSION_CODES,
    'CENTER_ADMIN': [
        'patients.view', 'patients.create', 'patients.edit',
        'records.view', 'records.create', 'records.edit',
        'appointments.view', 'appointments.manage',
        'pharmacy.manage', 'billing.view',
        'channels.use', 'channels.manage', 'reports.view', 'users.view',
    ],
    'DOCTOR': [
        'patients.view', 'patients.create', 'patients.edit',
        'records.view', 'records.create', 'records.edit', 'records.delete',
        'appointments.view', 'appointments.manage',
        'prescriptions.manage', 'channels.use', 'ai.use', 'reports.view',
    ],
    'NURSE': [
        'patients.view',
        'records.view', 'records.create',
        'appointments.view', 'appointments.manage',
        'channels.use',
    ],
    'LAB_TECH': [
        'patients.view', 'records.view', 'records.create', 'records.edit',
        'channels.use', 'reports.view',
    ],
    'PHARMACIST': [
        'patients.view', 'records.view', 'prescriptions.manage',
        'pharmacy.manage', 'channels.use',
    ],
    'AUDITOR': [
        'patients.view', 'records.view', 'reports.view', 'audit.view',
    ],
    'ACCOUNTANT': [
        'patients.view', 'billing.view', 'billing.manage', 'reports.view',
    ],
    'RECEPTIONIST': [
        'patients.view', 'patients.create',
        'appointments.view', 'appointments.manage',
        'billing.view', 'channels.use',
    ],
    'PATIENT': [
        'appointments.view', 'channels.use',
    ],
}


def permission_label(code):
    return _PERMISSIONS_BY_CODE.get(code, (code, 'أخرى'))[0]


def permission_category(code):
    return _PERMISSIONS_BY_CODE.get(code, (code, 'أخرى'))[1]


def default_allows(role, permission):
    """ما يقوله الافتراضي الثابت للدور."""
    if role == 'SUPER_ADMIN':
        return True
    return permission in DEFAULT_ROLE_PERMISSIONS.get(role, [])


def effective_allows(role, permission):
    """الحكم النهائي: تجاوز الإدارة الديناميكي أولاً ثم الافتراضي."""
    if role == 'SUPER_ADMIN':
        return True
    from apps.accounts.models import RolePermission
    override = RolePermission.objects.filter(role=role, permission=permission).first()
    if override is not None:
        return override.allowed
    return default_allows(role, permission)


def user_has_permission(user, permission):
    """نقطة التحقق الموحدة من الصلاحيات لكل الـ views."""
    if not getattr(user, 'is_authenticated', False):
        return False
    if user.is_superuser:
        return True
    return effective_allows(user.role, permission)


def role_permission_matrix():
    """مصفوفة كاملة (أدوار × صلاحيات) لواجهة الإدارة."""
    from apps.accounts.models import User, RolePermission

    overrides = {
        (op.role, op.permission): op.allowed
        for op in RolePermission.objects.all()
    }
    roles = [choice for choice in User.Role.choices]
    return {
        'permissions': [
            {'code': code, 'label': label, 'category': category}
            for code, label, category in PERMISSION_CATALOG
        ],
        'roles': [{'value': value, 'label': label} for value, label in roles],
        'matrix': {
            role_value: {
                code: {
                    'default': default_allows(role_value, code),
                    'effective': effective_allows(role_value, code),
                    'overridden': (role_value, code) in overrides,
                }
                for code in ALL_PERMISSION_CODES
            }
            for role_value, _role_label in roles
        },
    }
