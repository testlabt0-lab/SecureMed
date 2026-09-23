"""
Dynamic Data Masking (DDM) Engine for HIPAA & Saudi PDPL Compliance.

Masks Protected Health Information (PHI) and Personally Identifiable Information (PII)
at representation time according to the caller's role, channel assignment, and emergency
break-glass authorization.
"""
import logging
from typing import Optional, Dict, Any
from django.utils import timezone

logger = logging.getLogger('security')


def mask_national_id(national_id: Optional[str]) -> str:
    """Mask National ID preserving only the last 4 digits.
    Example: 1092837461 -> ******7461
    """
    if not national_id:
        return ""
    clean = str(national_id).strip()
    if len(clean) <= 4:
        return "****"
    return "*" * (len(clean) - 4) + clean[-4:]


def mask_phone(phone: Optional[str]) -> str:
    """Mask Phone number preserving country prefix and last 3 digits.
    Example: +966501234567 -> +96650****567
    """
    if not phone:
        return ""
    clean = str(phone).strip()
    if len(clean) <= 6:
        return "***"
    prefix_len = 5 if clean.startswith('+') else 3
    if len(clean) <= prefix_len + 3:
        return clean[:prefix_len] + "***"
    return clean[:prefix_len] + "*" * (len(clean) - prefix_len - 3) + clean[-3:]


def mask_name(full_name: Optional[str]) -> str:
    """Mask full name preserving the first name and initial of subsequent parts.
    Example: أحمد محمد الشهري -> أحمد م. ****
    Example: John Michael Doe -> John M. ****
    """
    if not full_name:
        return ""
    parts = str(full_name).strip().split()
    if len(parts) <= 1:
        return parts[0]
    first = parts[0]
    middle = f"{parts[1][0]}." if len(parts) > 1 and parts[1] else ""
    return f"{first} {middle} ****".strip()


def mask_address(address: Optional[str]) -> str:
    """Mask detailed street address while preserving general city/region if detected.
    Example: الرياض - حي الصحافة - شارع العليا -> الرياض - [عنوان محمي]
    """
    if not address:
        return ""
    clean = str(address).strip()
    separators = [' - ', '، ', ', ', '-']
    for sep in separators:
        if sep in clean:
            city = clean.split(sep)[0].strip()
            return f"{city} - [عنوان محمي]"
    return "[عنوان محمي]"


def should_unmask_patient(user, patient) -> bool:
    """Determine if the requesting user has legitimate clinical or administrative
    need to see unmasked PHI for this specific patient.
    
    Unmasked access is granted to:
    1. System Superadmins and Hospital Administrators.
    2. Direct Caregivers: Doctors or Nurses who are active members of an active
       clinical channel associated with this patient.
    3. Emergency Clinicians: When an active Break-Glass session exists.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False
        
    role = getattr(user, 'role', '')
    if role in ['SUPER_ADMIN', 'HOSPITAL_ADMIN']:
        return True

    # Patient themselves can view their own unmasked profile
    if role == 'PATIENT':
        linked_patient = getattr(user, 'patient_record', None)
        if linked_patient and linked_patient.pk == getattr(patient, 'pk', None):
            return True

    # Check for active Break-Glass emergency session
    try:
        from apps.security.models import BreakGlassAccess
        now = timezone.now()
        if BreakGlassAccess.objects.filter(
            user=user,
            patient=patient,
            status=BreakGlassAccess.Status.ACTIVE,
            expires_at__gt=now
        ).exists():
            return True
    except Exception as e:
        logger.debug(f"Break-Glass check error: {e}")

    # Check if user is a member of any of the patient's active channels
    try:
        from apps.channels.models import ChannelMembership
        if ChannelMembership.objects.filter(
            channel__patient=patient,
            user=user,
            is_active=True
        ).exists():
            return True
    except Exception as e:
        logger.debug(f"Channel membership check error: {e}")

    return False


def mask_patient_dict(data: Dict[str, Any], user, patient) -> Dict[str, Any]:
    """Apply dynamic masking rules to a serialized patient dictionary."""
    if should_unmask_patient(user, patient):
        return data

    masked = dict(data)
    if 'national_id' in masked and masked['national_id']:
        masked['national_id'] = mask_national_id(masked['national_id'])
        
    if 'phone' in masked and masked['phone']:
        masked['phone'] = mask_phone(masked['phone'])
        
    # Non-caregivers (e.g. Accountant, Receptionist, Lab Tech without direct channel)
    # also see masked address, emergency contact, and family name
    role = getattr(user, 'role', '') if user else ''
    if role not in ['DOCTOR', 'NURSE']:
        if 'full_name' in masked and masked['full_name']:
            masked['full_name'] = mask_name(masked['full_name'])
        if 'address' in masked and masked['address']:
            masked['address'] = mask_address(masked['address'])
        if 'emergency_contact' in masked and masked['emergency_contact']:
            masked['emergency_contact'] = mask_phone(masked['emergency_contact'])
            
    return masked
