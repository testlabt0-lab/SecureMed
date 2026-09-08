from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FHIRPatientViewSet, FHIRObservationViewSet

router = DefaultRouter()
router.register(r'Patient', FHIRPatientViewSet, basename='fhir-patient')
router.register(r'Observation', FHIRObservationViewSet, basename='fhir-observation')

urlpatterns = [
    path('fhir/', include(router.urls)),
]
