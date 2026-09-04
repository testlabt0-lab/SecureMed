"""URL configuration for appointments app."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.appointments.views import AppointmentViewSet, AppointmentSlotViewSet

router = DefaultRouter()
router.register(r'slots', AppointmentSlotViewSet, basename='appointment-slot')
router.register(r'', AppointmentViewSet, basename='appointment')

urlpatterns = [
    path('', include(router.urls)),
]
