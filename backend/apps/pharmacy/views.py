from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import F
from .models import Medication, Prescription

class PharmacyViewSet(viewsets.ViewSet):
    """
    ViewSet for Pharmacy operations.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def shortages(self, request):
        """
        Returns a list of medications that are at or below their reorder level.
        """
        shortages = Medication.objects.filter(
            stock_quantity__lte=F('reorder_level'),
            is_active=True
        ).values('id', 'name', 'stock_quantity', 'reorder_level')
        
        return Response({
            "status": "success",
            "count": len(shortages),
            "data": list(shortages)
        })
