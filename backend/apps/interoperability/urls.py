from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FHIRPatientViewSet

router = DefaultRouter()
router.register(r'Patient', FHIRPatientViewSet, basename='fhir-patient')

urlpatterns = [
    path('fhir/', include(router.urls)),
]
