"""Shared upload validation: extension allow-list + magic-byte signature check.

``MedicalFile`` grew this in ``apps.patients.models`` because its ``file`` field
is the upload clinicians download back. ``ChatMessage.attachment`` shipped with
*no validators at all* — no extension check, no size cap, no signature check —
so any authenticated member of a consultation could attach an arbitrary file
(huge, mislabelled, or a stored-XSS payload served from the same origin), and
``ProtectedMediaView`` explicitly documents that path as unvalidated.

The signature table and the content check live here now so both upload paths —
and any future one — share one source of truth. ``patients.validate_file_extension``
keeps its name and location (migration ``patients.0001_initial`` references the
function by path) and delegates here.
"""
import os

from django.core.exceptions import ValidationError

# Default attachment policy: documents and images a clinician actually sends in
# a consultation. Executable-adjacent formats (.html/.svg/.exe/.js) are absent
# on purpose — the media endpoint already forces anything not inline-safe to
# download with nosniff, but never accepting it is the stronger control.
DOCUMENT_EXTENSIONS =[
'.jpg','.jpeg','.png','.gif','.pdf','.txt',
'.doc','.docx','.xls','.xlsx','.csv',
]

# (offset, prefix) signatures keyed by extension family. Same table the patients
# app used; extended with the document formats above.
SIGNATURES ={
'.jpg':[(0 ,b'\xff\xd8\xff')],
'.jpeg':[(0 ,b'\xff\xd8\xff')],
'.png':[(0 ,b'\x89PNG\r\n\x1a\n')],
'.gif':[(0 ,b'GIF87a'),(0 ,b'GIF89a')],
'.pdf':[(0 ,b'%PDF-')],
'.txt':[],
'.csv':[],
# OLE2 container: legacy Word/Excel. Zip-based formats (.docx/.xlsx) start
# with the Zip local-file header.
'.doc':[(0 ,b'\xd0\xcf\x11\xe0')],
'.xls':[(0 ,b'\xd0\xcf\x11\xe0')],
'.docx':[(0 ,b'PK\x03\x04')],
'.xlsx':[(0 ,b'PK\x03\x04')],
# DICOM part-10 files carry 'DICM' after a 128-byte preamble; raw datasets
# begin with a group tag instead.
'.dcm':[(128 ,b'DICM'),(0 ,b'\x02\x00'),(0 ,b'\x08\x00')],
'.dicom':[(128 ,b'DICM'),(0 ,b'\x02\x00'),(0 ,b'\x08\x00')],
}

# Longest offset+prefix above, so one read covers every signature.
SIGNATURE_READ_LEN =132 +8

MAX_UPLOAD_BYTES =20 *1024 *1024 # 20MB


def _read_head (value ):
    """First bytes of an upload, leaving the file positioned back at the start.

    Failing open on an unreadable handle is deliberate: this check rejects
    mislabelled content, not storage hiccups — the size and permission checks
    are the ones that must be strict.
    """
    try :
        if hasattr (value ,'seek'):
            value .seek (0 )
        head =value .read (SIGNATURE_READ_LEN )
    except (OSError ,ValueError ):
        return None
    finally :
        try :
            if hasattr (value ,'seek'):
                value .seek (0 )
        except (OSError ,ValueError ):
            pass
    if isinstance (head ,str ):
        head =head .encode ('utf-8','replace')
    return head or None


def _content_matches (ext ,head ):
    """True when the head bytes are consistent with the claimed extension."""
    for offset ,prefix in SIGNATURES [ext ]:
        if head [offset :offset +len (prefix )]==prefix :
            return True
    return False


def validate_upload_content (value ,extensions ,max_bytes =MAX_UPLOAD_BYTES ):
    """Reject an upload whose extension, size or content is not allowed.

    The extension is a claim made by the uploader, so it is only the first
    gate; the magic bytes are the check that cannot be renamed around. Raise
    ValidationError with an Arabic message — these surface in DRF field errors.
    """
    ext =os .path .splitext (value .name or '')[1 ].lower ()
    if ext not in extensions :
        raise ValidationError (
        f'نوع الملف غير مدعوم. الأنواع المدعومة: {", ".join (extensions )}'
        )

    if value .size and value .size >max_bytes :
        raise ValidationError (
        f'حجم الملف كبير جداً. الحد الأقصى: {max_bytes // (1024 *1024 )} ميجابايت'
        )

    # Already-stored files are re-validated by full_clean() on existing rows;
    # their bytes were checked when uploaded and re-reading now costs a decrypt.
    if getattr (value ,'_committed',False ):
        return

    head =_read_head (value )
    if head is None :
        return

    if ext in ('.txt','.csv'):
        # Plain text has no signature. What matters here is that it is not a
        # disguised script or binary — '<' at offset 0 covers <script>/<svg.
        if head [:1 ]==b'<' :
            raise ValidationError (
            'محتوى الملف لا يطابق امتداده. قد يكون الملف خبيثاً.'
            )
        return

    if not _content_matches (ext ,head ):
        raise ValidationError (
        f'محتوى الملف لا يطابق امتداده ({ext }). قد يكون الملف تالفاً أو من نوع آخر.'
        )
