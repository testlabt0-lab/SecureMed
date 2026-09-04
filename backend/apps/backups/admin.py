"""Admin registration for the backups app."""
from django .contrib import admin 
from django .utils .translation import gettext_lazy as _ 

from apps .backups .models import BackupRecord 


@admin .register (BackupRecord )
class BackupRecordAdmin (admin .ModelAdmin ):
    list_display =[
    'filename','status','kind','size_kb','created_by',
    'exists_on_disk','created_at',
    ]
    list_filter =['status','kind']
    search_fields =['filename','note']
    readonly_fields =[
    'filename','filepath','size_bytes','checksum','status',
    'kind','row_counts','media_files','duration_ms',
    'created_by','note','created_at',
    ]

    @admin .display (description =_ ('الحجم (KB)'))
    def size_kb (self ,obj ):
        return round (obj .size_bytes /1024 ,1 )

    def has_add_permission (self ,request ):
    # Comment_142
        return False 
