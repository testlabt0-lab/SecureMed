"""Serializers for the backups app."""
from rest_framework import serializers

from apps.backups.models import BackupRecord


class BackupRecordSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source='created_by.full_name', read_only=True, default=''
    )
    kind_display = serializers.CharField(
        source='get_kind_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    exists_on_disk = serializers.BooleanField(read_only=True)
    size_kb = serializers.SerializerMethodField()

    class Meta:
        model = BackupRecord
        fields = [
            'id', 'filename', 'size_bytes', 'size_kb', 'checksum',
            'status', 'status_display', 'kind', 'kind_display',
            'row_counts', 'media_files', 'duration_ms',
            'created_by', 'created_by_name', 'note',
            'exists_on_disk', 'created_at',
        ]
        read_only_fields = fields

    def get_size_kb(self, obj):
        return round(obj.size_bytes / 1024, 1)
