"""
Arabic text helpers for PDF generation (reportlab does not shape Arabic).
Also registers the Unicode fonts used by the reports module.
"""
import os

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# DejaVu covers the Arabic block and is present on this system
FONT_DIR = '/usr/share/fonts/truetype/dejavu'
FONT_NORMAL = 'DejaVu'
FONT_BOLD = 'DejaVu-Bold'

_fonts_registered = False


def register_fonts():
    """Register DejaVu Sans (regular/bold) once per process."""
    global _fonts_registered
    if _fonts_registered:
        return
    pdfmetrics.registerFont(TTFont(
        FONT_NORMAL, os.path.join(FONT_DIR, 'DejaVuSans.ttf')
    ))
    pdfmetrics.registerFont(TTFont(
        FONT_BOLD, os.path.join(FONT_DIR, 'DejaVuSans-Bold.ttf')
    ))
    _fonts_registered = True


def ar(text) -> str:
    """Reshape + bidi-reorder Arabic text so reportlab renders it correctly."""
    if text is None:
        return ''
    text = str(text)
    if not text:
        return ''
    return get_display(arabic_reshaper.reshape(text))
