import re

def anonymize_patient_data(data):
    """
    Recursively remove or mask Personally Identifiable Information (PII)
    from dictionaries or strings before sending them to AI services.
    """
    if isinstance(data, dict):
        anonymized = {}
        for key, value in data.items():
            k_lower = key.lower()
            # Mask sensitive keys completely
            if any(sensitive in k_lower for sensitive in ['name', 'اسم', 'phone', 'هاتف', 'email', 'بريد', 'id', 'هوية', 'ssn', 'address', 'عنوان']):
                anonymized[key] = "[محذوف للخصوصية]"
            else:
                anonymized[key] = anonymize_patient_data(value)
        return anonymized
    elif isinstance(data, list):
        return [anonymize_patient_data(item) for item in data]
    elif isinstance(data, str):
        # Basic regex to mask potential phone numbers or IDs (strings of digits)
        # Masks any sequence of 5 or more digits
        masked_str = re.sub(r'\b\d{5,}\b', '[رقم مخفي]', data)
        # Mask emails
        masked_str = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[بريد مخفي]', masked_str)
        return masked_str
    else:
        return data
