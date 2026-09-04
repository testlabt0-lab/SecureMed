from unfold.admin import ModelAdmin
"""Admin registration for the basins app."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.basins.models import Basin


@admin.register(Basin)
class BasinAdmin(ModelAdmin):
    list_display = [
        'name', 'code', 'basin_type', 'governorate',
        'is_active', 'modules_count', 'created_at',
    ]
    list_filter = ['basin_type', 'is_active', 'governorate']
    search_fields = ['name', 'code', 'governorate', 'directorate']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = []

    fieldsets = (
        (_('البيانات الأساسية'), {
            'fields': ('name', 'code', 'basin_type', 'is_active')
        }),
        (_('الموقع'), {
            'fields': ('governorate', 'directorate', 'address')
        }),
        (_('التواصل والإدارة'), {
            'fields': ('phone', 'email', 'manager', 'bed_capacity')
        }),
        (_('الوحدات المفعّلة'), {
            'fields': ('enabled_modules',),
            'description': _('اتركها فارغة لتفعيل الافتراضي حسب نوع الحوض')
        }),
        (_('أخرى'), {'fields': ('notes', 'created_at', 'updated_at')}),
    )

    @admin.display(description=_('عدد الوحدات'))
    def modules_count(self, obj):
        return len(obj.enabled_modules or [])
