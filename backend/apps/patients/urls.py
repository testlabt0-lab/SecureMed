"""
URLs for patients app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.patients.views import PatientViewSet, MedicalRecordViewSet
from apps.patients.views_medical_file import MedicalFileViewSet
from apps.patients.portal import PatientPortalViewSet

router = DefaultRouter()
router.register(r'records', MedicalRecordViewSet, basename='medical-record')
router.register(r'files', MedicalFileViewSet, basename='medical-file')
# Must be registered BEFORE the bare '' prefix, whose detail route
# ^(?P<pk>[^/.]+)/$ would otherwise swallow 'portal'.
router.register(r'portal', PatientPortalViewSet, basename='patient-portal')
router.register(r'', PatientViewSet, basename='patient')

urlpatterns = [
    path('', include(router.urls)),
]
