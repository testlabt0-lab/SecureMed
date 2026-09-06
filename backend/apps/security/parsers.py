"""JSON parser that neutralises HTML markup **without** mangling plain text.

The previous implementation ran ``bleach.clean(..., strip=True)`` over every
string in every JSON request body. Bleach is an HTML sanitiser, so it also
HTML-escapes bare ``& < > " '`` in ordinary prose. Consequences, all silent:

* Credentials were rewritten on their way in. ``Xk9#mR2$vLp7&Qw3`` was stored
  as the hash of ``Xk9#mR2$vLp7&amp;Qw3``. Login through this parser escaped
  the same way and therefore "worked", which is why the defect survived — but
  the password on file was not the one the user chose, so any client that does
  not go through this parser (``createsuperuser``, ``INITIAL_ADMIN_PASSWORD``,
  the Django admin login form, a form-encoded POST) could never authenticate.
* Clinical free text was corrupted on every write: ``SpO2 < 90%`` became
  ``SpO2 &lt; 90%``, ``5mg & 10mg`` became ``5mg &amp; 10mg``. Read-edit-save
  round-trips compounded it (``&amp;`` → ``&amp;amp;``).

XSS is an output concern. The API renders JSON only and the SPA escapes when it
renders, so storing exactly what the clinician typed is both correct and safer.
What is kept here is the narrow part that has value: input which actually
carries markup is still run through bleach, so a stored ``<script>`` payload is
still stripped for any consumer that later renders a field as HTML.

Note the deliberate asymmetry that remains in ``DEFAULT_PARSER_CLASSES``: form
and multipart bodies are not sanitised. That is why input-side escaping cannot
be the primary XSS defence — it is bypassed by changing ``Content-Type``.
"""
import re

import bleach
from rest_framework.parsers import JSONParser

# An HTML tag, an HTML comment, or a character reference. Only strings that
# match are worth handing to an HTML sanitiser; everything else is prose,
# and prose must survive byte-for-byte.
_MARKUP = re.compile(r'</?[a-zA-Z][^>]*>|<!--|&#?\w{1,32};')

# Values that are credentials or opaque blobs: never rewritten, whatever they
# contain. Escaping one of these does not prevent an injection, it just locks
# the account out or invalidates the token.
_OPAQUE_KEY = re.compile(
    r'password|passwd|secret|token|credential|signature|assertion|challenge|'
    r'otp|totp|mfa|recovery|fingerprint|_key$|^key$|api_key|private_key|public_key',
    re.IGNORECASE,
)


class SanitizedJSONParser(JSONParser):
    """Parse JSON, then strip HTML from the values that actually contain it."""

    def parse(self, stream, media_type=None, parser_context=None):
        parsed_data = super().parse(stream, media_type, parser_context)
        return self._sanitize_data(parsed_data)

    def _sanitize_data(self, data, key=None):
        if isinstance(data, dict):
            return {k: self._sanitize_data(v, k) for k, v in data.items()}
        if isinstance(data, list):
            return [self._sanitize_data(item, key) for item in data]
        if isinstance(data, str):
            return self._sanitize_str(data, key)
        return data

    def _sanitize_str(self, text, key):
        if key is not None and _OPAQUE_KEY.search(str(key)):
            return text
        if not _MARKUP.search(text):
            return text
        return bleach.clean(
            text,
            tags=bleach.sanitizer.ALLOWED_TAGS,
            attributes=bleach.sanitizer.ALLOWED_ATTRIBUTES,
            strip=True,
        )
