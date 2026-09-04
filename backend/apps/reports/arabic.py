"""
Arabic text helpers for PDF generation (reportlab does not shape Arabic).
Also registers the Unicode fonts used by the reports module.
"""
import os 

import arabic_reshaper 
from bidi .algorithm import get_display 
from reportlab .pdfbase import pdfmetrics 
from reportlab .pdfbase .ttfonts import TTFont 

# Comment_282
if os .name =='nt':
    FONT_DIR ='C:\\Windows\\Fonts'
    FONT_NORMAL_FILE ='tahoma.ttf'
    FONT_BOLD_FILE ='tahomabd.ttf'
else :
    FONT_DIR ='/usr/share/fonts/truetype/dejavu'
    FONT_NORMAL_FILE ='DejaVuSans.ttf'
    FONT_BOLD_FILE ='DejaVuSans-Bold.ttf'

FONT_NORMAL ='DejaVu'
FONT_BOLD ='DejaVu-Bold'

_fonts_registered =False 


def register_fonts ():
    """Register DejaVu Sans (regular/bold) once per process."""
    global _fonts_registered 
    if _fonts_registered :
        return 

    normal_path =os .path .join (FONT_DIR ,FONT_NORMAL_FILE )
    bold_path =os .path .join (FONT_DIR ,FONT_BOLD_FILE )

    # Comment_283
    if not os .path .exists (normal_path ):
        import reportlab .rl_config 
        reportlab .rl_config .warnOnMissingFontGlyphs =0 
        return 

    pdfmetrics .registerFont (TTFont (FONT_NORMAL ,normal_path ))
    pdfmetrics .registerFont (TTFont (FONT_BOLD ,bold_path ))
    _fonts_registered =True 


def ar (text )->str :
    """Reshape + bidi-reorder Arabic text so reportlab renders it correctly."""
    if text is None :
        return ''
    text =str (text )
    if not text :
        return ''
    return get_display (arabic_reshaper .reshape (text ))
