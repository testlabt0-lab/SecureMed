"""Lab serializers."""
from rest_framework import serializers
from .models import LabTest, LabOrder, LabResult


class LabTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTest
        fields = '__all__'


class LabResultSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.CharField(source='performed_by.full_name', read_only=True)
    validated_by_name = serializers.CharField(source='validated_by.full_name', read_only=True, default=None)

    class Meta:
        model = LabResult
        fields = [
            'id', 'order', 'numeric_value', 'text_value',
            'is_abnormal', 'is_critical', 'notes',
            'performed_by', 'performed_by_name',
            'validated_by', 'validated_by_name', 'validated_at',
            'created_at',
        ]
        read_only_fields = ['is_abnormal', 'is_critical', 'validated_at']


class LabOrderSerializer(serializers.ModelSerializer):
    test_name = serializers.CharField(source='test.name', read_only=True)
    test_category = serializers.CharField(source='test.get_category_display', read_only=True)
    test_unit = serializers.CharField(source='test.unit', read_only=True)
    test_normal_range_min = serializers.DecimalField(source='test.normal_range_min', max_digits=10, decimal_places=3, read_only=True)
    test_normal_range_max = serializers.DecimalField(source='test.normal_range_max', max_digits=10, decimal_places=3, read_only=True)
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True)
    result = LabResultSerializer(read_only=True)

    class Meta:
        model = LabOrder
        fields = [
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'channel', 'test', 'test_name', 'test_category', 'test_unit',
            'test_normal_range_min', 'test_normal_range_max',
            'status', 'priority', 'clinical_notes', 'fasting_confirmed',
            'collected_at', 'collected_by', 'result',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_patient_name(self, obj):
        try:
            return obj.patient.full_name
        except Exception:
            return str(obj.patient_id)


class LabOrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabOrder
        fields = ['patient', 'channel', 'test', 'priority', 'clinical_notes', 'fasting_confirmed']

    def create(self, validated_data):
        return LabOrder.objects.create(
            doctor=self.context['request'].user,
            **validated_data
        )


class LabResultCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabResult
        fields = ['order', 'numeric_value', 'text_value', 'notes']

    def create(self, validated_data):
        return LabResult.objects.create(
            performed_by=self.context['request'].user,
            **validated_data
        )


class LabStatsSerializer(serializers.Serializer):
    total_tests = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    completed_today = serializers.IntegerField()
    critical_results = serializers.IntegerField()
    abnormal_results = serializers.IntegerField()
