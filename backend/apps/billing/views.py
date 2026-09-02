"""
Billing views — Invoices, payments, insurance management, and billing statistics.
"""
from datetime import timedelta

from django.db.models import Sum, Count, Q
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.utils import log_security_event

from .models import InsuranceProvider, PatientInsurance, Invoice, InvoiceItem
from .serializers import (
    InsuranceProviderSerializer,
    PatientInsuranceSerializer,
    InvoiceSerializer,
    InvoiceCreateSerializer,
    InvoiceItemSerializer,
    PaymentSerializer,
)


class InsuranceProviderViewSet(viewsets.ModelViewSet):
    """CRUD for insurance companies."""
    queryset = InsuranceProvider.objects.all()
    serializer_class = InsuranceProviderSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['name']


class PatientInsuranceViewSet(viewsets.ModelViewSet):
    """Patient insurance policies."""
    queryset = PatientInsurance.objects.select_related('provider').all()
    serializer_class = PatientInsuranceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        patient = self.request.query_params.get('patient')
        if patient:
            qs = qs.filter(patient_id=patient)
        return qs


class InvoiceViewSet(viewsets.ModelViewSet):
    """Invoice management — create, pay, cancel."""
    queryset = Invoice.objects.select_related('patient', 'created_by').prefetch_related('items').all()
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return InvoiceCreateSerializer
        return InvoiceSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        patient = self.request.query_params.get('patient')
        if patient:
            qs = qs.filter(patient_id=patient)
        search = self.request.query_params.get('search', '')
        if search:
            qs = qs.filter(
                Q(patient___full_name__icontains=search) |
                Q(id__icontains=search)
            )
        return qs

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """Process payment for an invoice."""
        invoice = self.get_object()
        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if invoice.status in ['PAID', 'CANCELLED']:
            return Response(
                {'detail': 'الفاتورة مدفوعة مسبقاً أو ملغاة'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment_method = serializer.validated_data.get('payment_method', 'CASH')

        invoice.status = 'PAID'
        invoice.save(update_fields=['status'])

        log_security_event(
            user=request.user,
            event_type='INVOICE_PAID',
            request=request,
            details={
                'invoice_id': str(invoice.id),
                'amount': str(invoice.final_total_with_vat),
                'method': payment_method,
            },
        )

        return Response(InvoiceSerializer(invoice).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an invoice."""
        invoice = self.get_object()
        if invoice.status == 'PAID':
            return Response(
                {'detail': 'لا يمكن إلغاء فاتورة مدفوعة'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        invoice.status = 'CANCELLED'
        invoice.save(update_fields=['status'])
        return Response(InvoiceSerializer(invoice).data)


class BillingStatsView(viewsets.ViewSet):
    """Billing dashboard statistics."""
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        today = timezone.now().date()
        month_start = today.replace(day=1)

        total = Invoice.objects.count()
        paid = Invoice.objects.filter(status='PAID').count()
        unpaid = Invoice.objects.filter(status__in=['UNPAID', 'PARTIAL', 'PENDING_INSURANCE']).count()

        total_revenue = Invoice.objects.filter(status='PAID').aggregate(
            total=Sum('patient_payable')
        )['total'] or 0

        pending_amount = Invoice.objects.filter(
            status__in=['UNPAID', 'PARTIAL']
        ).aggregate(total=Sum('patient_payable'))['total'] or 0

        insurance_collected = Invoice.objects.filter(status='PAID').aggregate(
            total=Sum('insurance_covered')
        )['total'] or 0

        today_revenue = Invoice.objects.filter(
            status='PAID', created_at__date=today
        ).aggregate(total=Sum('patient_payable'))['total'] or 0

        monthly_revenue = Invoice.objects.filter(
            status='PAID', created_at__date__gte=month_start
        ).aggregate(total=Sum('patient_payable'))['total'] or 0

        return Response({
            'total_invoices': total,
            'paid_invoices': paid,
            'unpaid_invoices': unpaid,
            'total_revenue': float(total_revenue),
            'pending_amount': float(pending_amount),
            'insurance_collected': float(insurance_collected),
            'today_revenue': float(today_revenue),
            'monthly_revenue': float(monthly_revenue),
        })
