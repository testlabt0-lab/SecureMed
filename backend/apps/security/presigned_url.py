"""
Presigned Expiring URL Signer for Secure Medical File Downloads.

Generates and validates cryptographically signed, tamper-evident, time-limited
download tokens for Protected Health Information (PHI) attachments and reports.
"""
import logging
from typing import Tuple, Optional
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.conf import settings

logger = logging.getLogger('security')

_SALT = 'securemed-presigned-download-v1'


def generate_presigned_token(file_id: str, user_id: str) -> str:
    """Generate a signed, timestamped token tied to a specific file and user.
    
    Args:
        file_id: UUID string of the medical file.
        user_id: UUID or ID string of the authorized user.
    """
    signer = TimestampSigner(salt=_SALT)
    payload = f"{file_id}:{user_id}"
    return signer.sign(payload)


def verify_presigned_token(token: str, file_id: str, max_age_seconds: int = 300) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate a presigned download token against a specific file and maximum age.
    
    Args:
        token: The signed token from the request query parameter.
        file_id: The target file UUID string.
        max_age_seconds: Maximum allowed token lifetime (default: 300 seconds / 5 minutes).
        
    Returns:
        (is_valid, authorized_user_id, failure_reason)
    """
    if not token or not file_id:
        return False, None, "رمز التحميل الموقّع مفقود"

    signer = TimestampSigner(salt=_SALT)
    try:
        unsigned = signer.unsign(token, max_age=max_age_seconds)
        parts = unsigned.split(':')
        if len(parts) != 2:
            return False, None, "صيغة رمز التحميل غير صالحة"
            
        token_file_id, token_user_id = parts
        if str(token_file_id) != str(file_id):
            return False, None, "رمز التحميل الموقّع لا يطابق الملف المطلوب"

        return True, token_user_id, None
    except SignatureExpired:
        return False, None, "انتهت صلاحية رابط التحميل الموقّع. يرجى طلب رابط جديد."
    except BadSignature:
        return False, None, "توقيع رابط التحميل غير صالح أو تم التلاعب به"
    except Exception as e:
        logger.warning(f"Presigned token verification error: {e}")
        return False, None, "فشل التحقق من أمان رابط التحميل"
