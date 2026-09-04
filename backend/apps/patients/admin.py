from unfold.admin import ModelAdmin
"""
Admin for patients app.
"""
from django.contrib import admin
from apps.patients.models import Patient, MedicalRecord, MedicalFile


@admin.register(Patient)
class PatientAdmin(ModelAdmin):
    list_display = ('id', 'date_of_birth', 'gender', 'blood_type', 'created_at')
    list_filter = ('gender', 'blood_type')
    readonly_fields = ('id', 'created_at', 'updated_at',
                       '_full_name', '_national_id', '_phone', '_address',
                       '_emergency_contact')


@admin.register(MedicalRecord)
class MedicalRecordAdmin(ModelAdmin):
    list_display = ('title', 'channel', 'record_type', 'created_by', 'is_critical')
    list_filter = ('record_type', 'is_critical')
    readonly_fields = ('id', '_content', 'created_at', 'updated_at')


@admin.register(MedicalFile)
class MedicalFileAdmin(ModelAdmin):
    list_display = ('title', 'channel', 'file_type', 'uploaded_by', 'file_size', 'is_critical', 'created_at')
    list_filter = ('file_type', 'is_critical')
    search_fields = ('title', 'original_filename', 'description')
    readonly_fields = ('id', 'file_size', 'mime_type', 'created_at', 'updated_at',
                       'access_count', 'last_accessed', 'last_accessed_by')
