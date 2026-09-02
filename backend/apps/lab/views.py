"""
Lab views — Test catalog, order management, results, and statistics.
"""
from django.db.models import Q, Count
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import LabTest, LabOrder, LabResult
from .serializers import (
    LabTestSerializer,
    LabOrderSerializer,
    LabOrderCreateSerializer,
    LabResultSerializer,
    LabResultCreateSerializer,
)


class LabTestViewSet(viewsets.ModelViewSet):
    """CRUD for the test catalog."""
    queryset = LabTest.objects.all()
    serializer_class = LabTestSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['name', 'code', 'category']
    ordering = ['category', 'name']

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search', '')
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(code__icontains=search))
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs


class LabOrderViewSet(viewsets.ModelViewSet):
    """Lab order management — create, collect sample, complete."""
    queryset = LabOrder.objects.select_related('patient', 'doctor', 'test', 'collected_by').all()
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return LabOrderCreateSerializer
        return LabOrderSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        st = self.request.query_params.get('status')
        if st:
            qs = qs.filter(status=st)
        priority = self.request.query_params.get('priority')
        if priority:
            qs = qs.filter(priority=priority)
        patient = self.request.query_params.get('patient')
        if patient:
            qs = qs.filter(patient_id=patient)
        return qs

    @action(detail=True, methods=['post'])
    def collect_sample(self, request, pk=None):
        """Mark that the sample has been collected."""
        order = self.get_object()
        if order.status != 'ORDERED':
            return Response({'detail': 'الطلب ليس في حالة "مطلوب"'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'SAMPLE_COLLECTED'
        order.collected_at = timezone.now()
        order.collected_by = request.user
        order.save(update_fields=['status', 'collected_at', 'collected_by'])
        return Response(LabOrderSerializer(order).data)

    @action(detail=True, methods=['post'])
    def start_processing(self, request, pk=None):
        """Mark the order as in progress."""
        order = self.get_object()
        if order.status != 'SAMPLE_COLLECTED':
            return Response({'detail': 'يجب جمع العينة أولاً'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'IN_PROGRESS'
        order.save(update_fields=['status'])
        return Response(LabOrderSerializer(order).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a lab order."""
        order = self.get_object()
        if order.status in ['COMPLETED', 'VALIDATED']:
            return Response({'detail': 'لا يمكن إلغاء طلب مكتمل'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'CANCELLED'
        order.save(update_fields=['status'])
        return Response(LabOrderSerializer(order).data)


class LabResultViewSet(viewsets.ModelViewSet):
    """Enter and validate lab results."""
    queryset = LabResult.objects.select_related('order__test', 'order__patient', 'performed_by', 'validated_by').all()
    serializer_class = LabResultSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return LabResultCreateSerializer
        return LabResultSerializer

    def perform_create(self, serializer):
        result = serializer.save()
        # Update order status to COMPLETED
        order = result.order
        order.status = 'COMPLETED'
        order.save(update_fields=['status'])

    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """Doctor validates a lab result."""
        result = self.get_object()
        result.validated_by = request.user
        result.validated_at = timezone.now()
        result.save(update_fields=['validated_by', 'validated_at'])
        # Update order status
        result.order.status = 'VALIDATED'
        result.order.save(update_fields=['status'])
        return Response(LabResultSerializer(result).data)

    @action(detail=False, methods=['get'])
    def critical(self, request):
        """List all critical results."""
        critical = self.get_queryset().filter(is_critical=True).order_by('-created_at')[:50]
        return Response(LabResultSerializer(critical, many=True).data)

    @action(detail=False, methods=['get'])
    def abnormal(self, request):
        """List all abnormal results."""
        abnormal = self.get_queryset().filter(is_abnormal=True).order_by('-created_at')[:50]
        return Response(LabResultSerializer(abnormal, many=True).data)


class LabStatsView(viewsets.ViewSet):
    """Lab dashboard statistics."""
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        today = timezone.now().date()
        return Response({
            'total_tests': LabTest.objects.filter(is_active=True).count(),
            'pending_orders': LabOrder.objects.filter(status__in=['ORDERED', 'SAMPLE_COLLECTED']).count(),
            'in_progress': LabOrder.objects.filter(status='IN_PROGRESS').count(),
            'completed_today': LabOrder.objects.filter(status__in=['COMPLETED', 'VALIDATED'], updated_at__date=today).count(),
            'critical_results': LabResult.objects.filter(is_critical=True).count(),
            'abnormal_results': LabResult.objects.filter(is_abnormal=True).count(),
        })
