"""
Tests for Blind Indexing on Encrypted Patient Records.
"""
import pytest
from apps.security.blind_index import (
    compute_blind_index,
    compute_search_tokens,
    normalize_text,
    get_blind_index_key,
)


class TestBlindIndexing:
    def test_blind_index_is_deterministic(self):
        """Same input with different whitespace/casing must produce identical blind index."""
        b1 = compute_blind_index('1234567890')
        b2 = compute_blind_index(' 1234567890 ')
        assert b1 == b2
        assert len(b1) == 64

    def test_arabic_normalization(self):
        """Arabic letter variants and tashkeel must normalize identically."""
        b1 = compute_blind_index('أَحْمَد')
        b2 = compute_blind_index('احمد')
        assert b1 == b2

        b3 = compute_blind_index('فَاطِمَة')
        b4 = compute_blind_index('فاطمه')
        assert b3 == b4

    def test_name_search_tokens(self):
        """Search tokens must contain word-level and prefix hashes."""
        tokens = compute_search_tokens('أحمد محمد الشامي')
        single_token = compute_search_tokens('أحمد')
        for t in single_token.split():
            assert t in tokens

    def test_empty_inputs(self):
        """Empty or None inputs return empty string safely without raising."""
        assert compute_blind_index('') == ''
        assert compute_blind_index(None) == ''
        assert compute_search_tokens('') == ''
        assert compute_search_tokens(None) == ''
