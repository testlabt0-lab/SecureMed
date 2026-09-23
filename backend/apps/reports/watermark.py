"""
Dynamic PDF Security Watermarking Engine for SecureMed Clinical Reports.

Stamps downloaded or exported PDF reports with tamper-evident digital attribution
including user name, role, IP address, and exact download timestamp.
"""
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from .arabic import ar, FONT_NORMAL, FONT_BOLD


def draw_pdf_security_watermark(canvas, doc, user=None, ip=""):
    """Callback for ReportLab SimpleDocTemplate (onFirstPage and onLaterPages).
    
    Draws a light diagonal watermark in the page center and an auditable
    attribution footer.
    """
    canvas.saveState()

    # 1. Subtle diagonal watermark across page center
    canvas.setFont(FONT_BOLD, 28)
    canvas.setFillColor(colors.Color(0.85, 0.85, 0.88, alpha=0.15))
    canvas.translate(A4[0] / 2.0, A4[1] / 2.0)
    canvas.rotate(45)

    user_str = getattr(user, 'full_name', '') or getattr(user, 'email', '') or "Authorized Clinician"
    watermark_text = ar(f"SECUREMED • {user_str}")
    canvas.drawCentredString(0, 0, watermark_text)
    canvas.restoreState()

    # 2. Strict footer with user attribution, IP, and UTC timestamp
    canvas.saveState()
    canvas.setFont(FONT_NORMAL, 7.5)
    canvas.setFillColor(colors.HexColor('#64748B'))
    timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    ip_str = f" | IP: {ip}" if ip else ""
    role_str = f" ({getattr(user, 'role', '')})" if getattr(user, 'role', None) else ""
    footer_text = ar(f"نسخة طبية معتمدة ومقيدة — تم التنزيل بواسطة: {user_str}{role_str}{ip_str} | {timestamp}")
    canvas.drawCentredString(A4[0] / 2.0, 8 * mm, footer_text)
    canvas.restoreState()
