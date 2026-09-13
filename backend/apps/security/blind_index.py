"""
Blind Indexing cryptographic utility for SecureMed.

Provides deterministic, keyed HMAC hashes for searching encrypted data
without decrypting database records or exposing plaintext in indexes.
Supports Arabic normalization and word-level token hashing.
"""
import re
import hmac
import hashlib
from django.conf import settings


def get_blind_index_key() -> bytes:
    """
    Retrieve or derive the secret key dedicated to blind indexing.
    Falls back to deriving from ENCRYPTION_KEY or SECRET_KEY so zero configuration
    is required, while maintaining domain separation with a unique salt.
    """
    custom_key = getattr(settings, 'BLIND_INDEX_KEY', None)
    if custom_key:
        if isinstance(custom_key, str):
            return custom_key.encode('utf-8')
        return custom_key

    enc_key = getattr(settings, 'ENCRYPTION_KEY', '') or getattr(settings, 'SECRET_KEY', 'securemed-default')
    if isinstance(enc_key, str):
        enc_key = enc_key.encode('utf-8')
    return hmac.new(enc_key, b'securemed-blind-index-salt-v1', hashlib.sha256).digest()


def normalize_text(text: str) -> str:
    """
    Normalize text for indexing and searching.
    - Strips leading/trailing whitespace
    - Lowercases Latin characters
    - Normalizes Arabic letter variants (أ/إ/آ -> ا, ة -> ه, ى -> ي)
    - Removes Arabic diacritics (tashkeel)
    """
    if not text:
        return ''
    cleaned = str(text).strip().lower()

    # Remove Arabic Tashkeel
    tashkeel_re = re.compile(r'[\u064B-\u0652\u0670]')
    cleaned = tashkeel_re.sub('', cleaned)

    arabic_char_map = {
        'أ': 'ا',
        'إ': 'ا',
        'آ': 'ا',
        'ٱ': 'ا',
        'ة': 'ه',
        'ى': 'ي',
    }
    for orig, target in arabic_char_map.items():
        cleaned = cleaned.replace(orig, target)

    cleaned = re.sub(r'[\-_,.\s]+', ' ', cleaned).strip()
    return cleaned


def compute_blind_index(value: str) -> str:
    """
    Compute a 64-character hex HMAC-SHA256 blind index for exact field matching
    (e.g., National ID or Phone Number).
    """
    if not value:
        return ''
    normalized = normalize_text(value)
    if not normalized:
        return ''
    key = get_blind_index_key()
    return hmac.new(key, normalized.encode('utf-8'), hashlib.sha256).hexdigest()


def compute_search_tokens(text: str) -> str:
    """
    Generate space-separated blind index token hashes for multi-word full text search
    (e.g., Patient Full Name). Each word of 2+ characters receives a 16-char HMAC.
    Also includes prefix tokens (3 to 6 chars) for fast prefix searching.
    """
    if not text:
        return ''
    normalized = normalize_text(text)
    if not normalized:
        return ''

    words = [w for w in normalized.split() if len(w) >= 2]
    if not words:
        words = [normalized]

    key = get_blind_index_key()
    tokens = set()
    for word in words:
        tokens.add(word)
        for length in range(3, min(len(word), 7)):
            tokens.add(word[:length])

    token_hashes = []
    seen = set()
    for t in tokens:
        th = hmac.new(key, t.encode('utf-8'), hashlib.sha256).hexdigest()[:16]
        if th not in seen:
            seen.add(th)
            token_hashes.append(th)

    return ' '.join(token_hashes)
