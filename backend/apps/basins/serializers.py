"""Serializers for the basins app."""
from rest_framework import serializers

from apps.basins.models import Basin


class BasinSerializer(serializers.ModelSerializer):
    basin_type_display = serializers.CharField(
        source='get_basin_type_display', read_only=True
    )
    manager_name = serializers.CharField(
        source='manager.full_name', read_only=True, default=''
    )
    modules_detail = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()

    class Meta:
        model = Basin
        fields = [
            'id', 'name', 'code', 'basin_type', 'basin_type_display',
            'governorate', 'directorate', 'address', 'phone', 'email',
            'manager', 'manager_name', 'bed_capacity',
            'enabled_modules', 'modules_detail',
            'is_active', 'notes', 'stats',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_modules_detail(self, obj):
        return [
            {'key': m, 'label': str(Basin.MODULE_LABELS.get(m, m)),
             'enabled': obj.has_module(m)}
            for m in Basin.ALL_MODULES
        ]

    def get_stats(self, obj):
        # Cheap on list views at demo scale; exact counts per basin.
        return obj.stats()

    def validate_enabled_modules(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('يجب أن تكون قائمة وحدات')
        unknown = [m for m in value if m not in Basin.ALL_MODULES]
        if unknown:
            raise serializers.ValidationError(
                f'وحدات غير معروفة: {", ".join(unknown)}'
            )
        return list(dict.fromkeys(value))  # de-duplicate, keep order


class BasinStatsSerializer(serializers.Serializer):
    """Aggregated system-wide basin statistics (admin dashboard)."""
    total = serializers.IntegerField()
    active = serializers.IntegerField()
    by_type = serializers.DictField(child=serializers.IntegerField())
