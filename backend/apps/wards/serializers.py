"""
Ward management serializers.
"""
from rest_framework import serializers
from .models import Ward, Room, Bed, BedAssignment


class BedSerializer(serializers.ModelSerializer):
    room_number = serializers.CharField(source='room.room_number', read_only=True)
    room_type = serializers.CharField(source='room.get_room_type_display', read_only=True)
    ward_name = serializers.CharField(source='room.ward.name', read_only=True)

    class Meta:
        model = Bed
        fields = ['id', 'room', 'room_number', 'room_type', 'ward_name', 'bed_number', 'status', 'notes']


class RoomSerializer(serializers.ModelSerializer):
    beds = BedSerializer(many=True, read_only=True)
    ward_name = serializers.CharField(source='ward.name', read_only=True)

    class Meta:
        model = Room
        fields = ['id', 'ward', 'ward_name', 'room_number', 'room_type', 'is_active', 'beds']


class WardSerializer(serializers.ModelSerializer):
    rooms = RoomSerializer(many=True, read_only=True)
    total_beds = serializers.SerializerMethodField()
    occupied_beds = serializers.SerializerMethodField()

    class Meta:
        model = Ward
        fields = ['id', 'name', 'floor', 'description', 'is_active', 'rooms', 'total_beds', 'occupied_beds']

    def get_total_beds(self, obj):
        return Bed.objects.filter(room__ward=obj).count()

    def get_occupied_beds(self, obj):
        return Bed.objects.filter(room__ward=obj, status='OCCUPIED').count()


class BedAssignmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    admitted_by_name = serializers.CharField(source='admitted_by.full_name', read_only=True)
    bed_details = BedSerializer(source='bed', read_only=True)

    class Meta:
        model = BedAssignment
        fields = [
            'id', 'bed', 'bed_details', 'patient', 'patient_name',
            'admitted_by', 'admitted_by_name', 'admission_date',
            'discharge_date', 'diagnosis_on_admission', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'admitted_by', 'admission_date', 'discharge_date', 'is_active', 'created_at', 'updated_at']

    def get_patient_name(self, obj):
        try:
            return obj.patient.full_name
        except Exception:
            return str(obj.patient_id)


class BedAssignmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BedAssignment
        fields = ['bed', 'patient', 'diagnosis_on_admission']

    def create(self, validated_data):
        bed = validated_data['bed']
        
        # Verify bed is free
        if bed.status != 'FREE':
            raise serializers.ValidationError({"bed": "السرير غير متاح حالياً."})
            
        # Verify patient is not already admitted
        if BedAssignment.objects.filter(patient=validated_data['patient'], is_active=True).exists():
            raise serializers.ValidationError({"patient": "المريض منوّم حالياً في سرير آخر."})

        assignment = BedAssignment.objects.create(
            admitted_by=self.context['request'].user,
            **validated_data
        )
        
        # Update bed status
        bed.status = 'OCCUPIED'
        bed.save(update_fields=['status'])
        
        return assignment
