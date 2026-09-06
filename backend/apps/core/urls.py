from django.urls import path
from .views import OfflineSyncAPIView

urlpatterns = [
    path('sync/', OfflineSyncAPIView.as_view(), name='offline-sync'),
]
