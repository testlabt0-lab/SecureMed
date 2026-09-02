"""Admin registration for appointments app."""
from django.contrib import admin
from apps.appointments.models import Appointment, AppointmentSlot


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'patient', 'doctor', 'appointment_type', 'status', 'scheduled_at', 'priority']
    list_filter = ['status', 'appointment_type', 'priority', 'is_virtual']
    search_fields = ['title', 'patient__full_name', 'doctor__full_name', 'notes']
    ordering = ['-scheduled_at']
    readonly_fields = ['id', 'created_at', 'updated_at', 'cancelled_at']
    date_hierarchy = 'scheduled_at'


@admin.register(AppointmentSlot)
class AppointmentSlotAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'day_of_week', 'start_time', 'end_time', 'slot_duration_minutes', 'is_active']
    list_filter = ['day_of_week', 'is_active']
    search_fields = ['doctor__full_name']
