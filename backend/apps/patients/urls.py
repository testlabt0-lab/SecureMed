"""
URLs for patients app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.patients.views import PatientViewSet, MedicalRecordViewSet
from apps.patients.views_medical_file import MedicalFileViewSet

router = DefaultRouter()
router.register(r'', PatientViewSet, basename='patient')
router.register(r'records', MedicalRecordViewSet, basename='medical-record')
router.register(r'files', MedicalFileViewSet, basename='medical-file')

urlpatterns = [
    path('', include(router.urls)),
]
