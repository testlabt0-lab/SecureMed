"""
Billing serializers — Invoices, payments, insurance.
"""
from rest_framework import serializers

from .models import InsuranceProvider, PatientInsurance, Invoice, InvoiceItem


class InsuranceProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsuranceProvider
        fields = ['id', 'name', 'contact_email', 'contact_phone', 'api_endpoint', 'is_active']


class PatientInsuranceSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)

    class Meta:
        model = PatientInsurance
        fields = [
            'id', 'patient', 'provider', 'provider_name',
            'policy_number', 'coverage_percentage',
            'expiry_date', 'is_valid',
        ]


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ['id', 'description', 'quantity', 'unit_price', 'total_price']
        read_only_fields = ['total_price']


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    patient_name = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    vat_amount = serializers.FloatField(read_only=True)
    final_total_with_vat = serializers.FloatField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'patient', 'patient_name', 'created_by', 'created_by_name',
            'total_amount', 'discount', 'insurance_covered', 'patient_payable',
            'vat_amount', 'final_total_with_vat',
            'status', 'due_date', 'items', 'created_at',
        ]
        read_only_fields = ['id', 'vat_amount', 'final_total_with_vat', 'created_at']

    def get_patient_name(self, obj):
        try:
            return obj.patient.full_name
        except Exception:
            return str(obj.patient_id)


class InvoiceCreateSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True)

    class Meta:
        model = Invoice
        fields = ['patient', 'discount', 'due_date', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        invoice = Invoice.objects.create(
            created_by=self.context['request'].user,
            **validated_data
        )
        total = 0
        for item_data in items_data:
            item = InvoiceItem.objects.create(invoice=invoice, **item_data)
            total += float(item.total_price)

        invoice.total_amount = total
        invoice.patient_payable = total - float(invoice.discount)

        # Auto-apply insurance if available
        from .models import PatientInsurance
        active_insurance = PatientInsurance.objects.filter(
            patient=invoice.patient, is_valid=True
        ).first()
        if active_insurance:
            coverage = float(active_insurance.coverage_percentage) / 100
            invoice.insurance_covered = round(float(invoice.patient_payable) * coverage, 2)
            invoice.patient_payable = round(float(invoice.patient_payable) - float(invoice.insurance_covered), 2)

        invoice.status = 'UNPAID'
        invoice.save()
        return invoice


class PaymentSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(
        choices=['CASH', 'CREDIT_CARD', 'BANK_TRANSFER', 'INSURANCE'],
        default='CASH',
    )
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    notes = serializers.CharField(max_length=500, required=False, default='')


class BillingStatsSerializer(serializers.Serializer):
    total_invoices = serializers.IntegerField()
    paid_invoices = serializers.IntegerField()
    unpaid_invoices = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    pending_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    insurance_collected = serializers.DecimalField(max_digits=14, decimal_places=2)
    today_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    monthly_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
