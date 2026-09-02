"""
Ward management views.
"""
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Ward, Room, Bed, BedAssignment
from .serializers import (
    WardSerializer,
    RoomSerializer,
    BedSerializer,
    BedAssignmentSerializer,
    BedAssignmentCreateSerializer,
)


class WardViewSet(viewsets.ModelViewSet):
    """CRUD for Wards."""
    queryset = Ward.objects.all()
    serializer_class = WardSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['name']


class RoomViewSet(viewsets.ModelViewSet):
    """CRUD for Rooms."""
    queryset = Room.objects.select_related('ward').all()
    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['ward', 'room_number']


class BedViewSet(viewsets.ModelViewSet):
    """CRUD for Beds."""
    queryset = Bed.objects.select_related('room__ward').all()
    serializer_class = BedSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['room', 'bed_number']

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        ward_id = self.request.query_params.get('ward')
        if ward_id:
            qs = qs.filter(room__ward_id=ward_id)
        return qs

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Update bed status manually (e.g. for maintenance/cleaning)."""
        bed = self.get_object()
        new_status = request.data.get('status')
        if new_status not in [s[0] for s in Bed.Status.choices]:
            return Response({'detail': 'حالة غير صالحة'}, status=status.HTTP_400_BAD_REQUEST)
            
        if bed.status == 'OCCUPIED' and new_status != 'OCCUPIED':
            return Response({'detail': 'لا يمكن تغيير حالة سرير مشغول إلا بخروج المريض'}, status=status.HTTP_400_BAD_REQUEST)

        bed.status = new_status
        bed.save(update_fields=['status'])
        return Response(BedSerializer(bed).data)


class BedAssignmentViewSet(viewsets.ModelViewSet):
    """Patient admission and discharge."""
    queryset = BedAssignment.objects.select_related('patient', 'bed__room__ward', 'admitted_by').all()
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['-admission_date']

    def get_serializer_class(self):
        if self.action == 'create':
            return BedAssignmentCreateSerializer
        return BedAssignmentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        active = self.request.query_params.get('active')
        if active == 'true':
            qs = qs.filter(is_active=True)
        elif active == 'false':
            qs = qs.filter(is_active=False)
        return qs

    @action(detail=True, methods=['post'])
    def discharge(self, request, pk=None):
        """Discharge a patient and free the bed."""
        assignment = self.get_object()
        if not assignment.is_active:
            return Response({'detail': 'المريض تم إخراجه مسبقاً'}, status=status.HTTP_400_BAD_REQUEST)

        assignment.is_active = False
        assignment.discharge_date = timezone.now()
        assignment.save(update_fields=['is_active', 'discharge_date'])

        # Free the bed (or mark for cleaning)
        bed = assignment.bed
        bed.status = 'CLEANING'
        bed.save(update_fields=['status'])

        return Response(BedAssignmentSerializer(assignment).data)


class WardStatsView(viewsets.ViewSet):
    """Ward dashboard statistics."""
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        total_beds = Bed.objects.count()
        occupied_beds = Bed.objects.filter(status='OCCUPIED').count()
        free_beds = Bed.objects.filter(status='FREE').count()
        maintenance_cleaning = Bed.objects.filter(status__in=['MAINTENANCE', 'CLEANING']).count()
        
        active_admissions = BedAssignment.objects.filter(is_active=True).count()
        discharged_today = BedAssignment.objects.filter(
            is_active=False, discharge_date__date=timezone.now().date()
        ).count()
        admitted_today = BedAssignment.objects.filter(
            admission_date__date=timezone.now().date()
        ).count()

        occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0

        return Response({
            'total_beds': total_beds,
            'occupied_beds': occupied_beds,
            'free_beds': free_beds,
            'maintenance_cleaning': maintenance_cleaning,
            'occupancy_rate': round(occupancy_rate, 1),
            'active_admissions': active_admissions,
            'admitted_today': admitted_today,
            'discharged_today': discharged_today,
        })
