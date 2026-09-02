"""
Pharmacy serializers — Medication inventory, prescriptions, stock tracking.
"""
from rest_framework import serializers
from django.utils import timezone

from .models import Medication, DrugInteraction, Prescription, PrescriptionItem


class MedicationSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = Medication
        fields = [
            'id', 'name', 'scientific_name', 'barcode',
            'stock_quantity', 'reorder_level', 'unit_price',
            'expiry_date', 'description', 'instructions',
            'is_active', 'is_low_stock', 'is_expired',
        ]

    def get_is_low_stock(self, obj):
        return obj.stock_quantity <= obj.reorder_level

    def get_is_expired(self, obj):
        if obj.expiry_date:
            return obj.expiry_date < timezone.now().date()
        return False


class DrugInteractionSerializer(serializers.ModelSerializer):
    drug_a_name = serializers.CharField(source='drug_a.name', read_only=True)
    drug_b_name = serializers.CharField(source='drug_b.name', read_only=True)

    class Meta:
        model = DrugInteraction
        fields = [
            'id', 'drug_a', 'drug_b', 'drug_a_name', 'drug_b_name',
            'severity', 'description',
        ]


class PrescriptionItemSerializer(serializers.ModelSerializer):
    medication_name = serializers.CharField(source='medication.name', read_only=True)
    medication_stock = serializers.IntegerField(source='medication.stock_quantity', read_only=True)

    class Meta:
        model = PrescriptionItem
        fields = [
            'id', 'medication', 'medication_name', 'medication_stock',
            'dosage', 'frequency', 'duration_days', 'quantity',
        ]


class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True, read_only=True)
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True)

    class Meta:
        model = Prescription
        fields = [
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'diagnosis_code', 'digital_signature', 'is_signed', 'signed_at',
            'notes', 'status', 'items', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'digital_signature', 'is_signed', 'signed_at', 'created_at', 'updated_at']

    def get_patient_name(self, obj):
        try:
            return obj.patient.full_name
        except Exception:
            return str(obj.patient_id)


class PrescriptionCreateSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True)

    class Meta:
        model = Prescription
        fields = ['patient', 'diagnosis_code', 'notes', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        prescription = Prescription.objects.create(
            doctor=self.context['request'].user,
            **validated_data
        )
        for item_data in items_data:
            PrescriptionItem.objects.create(prescription=prescription, **item_data)
        return prescription


class StockMovementSerializer(serializers.Serializer):
    """Serializer for recording stock adjustments."""
    medication_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    movement_type = serializers.ChoiceField(choices=['IN', 'OUT', 'ADJUSTMENT', 'RETURN'])
    reason = serializers.CharField(max_length=500, required=False, default='')


class DispensePrescriptionSerializer(serializers.Serializer):
    """Serializer for dispensing a prescription."""
    notes = serializers.CharField(max_length=500, required=False, default='')


class PharmacyStatsSerializer(serializers.Serializer):
    total_medications = serializers.IntegerField()
    low_stock_count = serializers.IntegerField()
    expired_count = serializers.IntegerField()
    total_prescriptions = serializers.IntegerField()
    pending_prescriptions = serializers.IntegerField()
    dispensed_today = serializers.IntegerField()
    total_stock_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    expiring_soon = serializers.IntegerField()
