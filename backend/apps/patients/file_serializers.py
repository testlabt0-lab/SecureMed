"""
Serializers for medical file uploads.
"""
from rest_framework import serializers 
from apps .patients .file_models import MedicalFile 


class MedicalFileSerializer (serializers .ModelSerializer ):
    """Serializer for medical files."""
    uploaded_by_name =serializers .CharField (
    source ='uploaded_by.full_name',read_only =True 
    )
    file_type_display =serializers .CharField (
    source ='get_file_type_display',read_only =True 
    )
    file_size_display =serializers .CharField (read_only =True )
    description =serializers .CharField (required =False ,allow_blank =True )

    class Meta :
        model =MedicalFile 
        fields =[
        'id','channel','file_type','file_type_display',
        'file','original_filename','file_size','file_size_display',
        'mime_type','description','uploaded_by','uploaded_by_name',
        'is_critical','created_at',
        ]
        read_only_fields =[
        'id','original_filename','file_size','mime_type',
        'uploaded_by','uploaded_by_name','created_at',
        'file_size_display',
        ]


class MedicalFileUploadSerializer (serializers .ModelSerializer ):
    """Serializer for uploading medical files."""
    description =serializers .CharField (required =False ,allow_blank =True )

    class Meta :
        model =MedicalFile 
        fields =['channel','file_type','file','description','is_critical']

    def validate_file (self ,value ):
        """Validate uploaded file."""
        # Comment_226
        if value .size >10 *1024 *1024 :
            raise serializers .ValidationError (
            'حجم الملف يجب أن يكون أقل من 10 ميجابايت'
            )
            # Comment_227
        allowed_extensions =[
        '.jpg','.jpeg','.png','.gif','.bmp',
        '.pdf','.doc','.docx',
        '.dcm',# Comment_228
        ]
        import os 
        ext =os .path .splitext (value .name )[1 ].lower ()
        if ext not in allowed_extensions :
            raise serializers .ValidationError (
            f'نوع الملف غير مسموح. الأنواع المسموحة: {", ".join (allowed_extensions )}'
            )
        return value 

    def create (self ,validated_data ):
        file_obj =validated_data ['file']
        import os 
        validated_data ['original_filename']=file_obj .name 
        validated_data ['file_size']=file_obj .size 
        validated_data ['mime_type']=getattr (file_obj ,'content_type','')
        validated_data ['uploaded_by']=self .context ['request'].user 
        return super ().create (validated_data )
