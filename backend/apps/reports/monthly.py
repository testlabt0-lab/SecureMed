"""
Reusable monthly report builder.
---------------------------
Extracted from MonthlyReportPDFView so the exact same PDF can be:
- downloaded from the UI  (reports.views)
- emailed on demand       (reports.views.MonthlyReportEmailView)
- emailed by cron/scheduler (management command send_scheduled_reports)
"""
import io
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('Agg')  # headless
import matplotlib.pyplot as plt

from django.utils import timezone
from django.db.models import Count

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)

from apps.accounts.models import User
from apps.channels.models import Channel, ChannelMessage
from apps.patients.models import Patient, MedicalRecord
from apps.audit.models import AuditLog

from .arabic import ar, register_fonts, FONT_NORMAL, FONT_BOLD

BRAND = colors.HexColor('#2563EB')
BRAND_DARK = colors.HexColor('#1E40AF')
LIGHT_ROW = colors.HexColor('#EFF6FF')
GRID = colors.HexColor('#BFDBFE')


def _mpl_ar(text: str) -> str:
    """Arabic shaping for matplotlib labels."""
    import arabic_reshaper
    from bidi.algorithm import get_display
    return get_display(arabic_reshaper.reshape(str(text)))


def _chart_bytes(fig) -> io.BytesIO:
    """Render a matplotlib figure to a seeked BytesIO (reportlab-friendly)."""
    buf = io.BytesIO()
    fig.savefig(buf, format='PNG', dpi=140, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


def build_monthly_report(month_str: str | None = None,
                         generated_by: str = 'النظام') -> tuple[bytes, str, datetime]:
    """
    Build the monthly performance & security PDF.

    Returns (pdf_bytes, filename, period_start_datetime).
    `month_str` format: 'YYYY-MM' (None → current month).
    """
    register_fonts()
    now = timezone.localtime(timezone.now())
    try:
        start = (
            datetime.strptime(month_str, '%Y-%m').replace(tzinfo=now.tzinfo)
            if month_str else now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        )
    except ValueError as exc:
        raise ValueError('صيغة الشهر غير صحيحة (YYYY-MM)') from exc
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)

    channels = Channel.objects.filter(created_at__range=(start, end))
    patients = Patient.objects.filter(created_at__range=(start, end))
    records = MedicalRecord.objects.filter(created_at__range=(start, end))
    logs = AuditLog.objects.filter(timestamp__range=(start, end))
    messages = ChannelMessage.objects.filter(created_at__range=(start, end))

    # ---- Charts ----
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    # Channels by type (pie)
    type_counts = list(channels.values('channel_type').annotate(n=Count('id')))
    labels, sizes = [], []
    type_names = dict(Channel.ChannelType.choices)
    for row in type_counts:
        labels.append(_mpl_ar(type_names.get(row['channel_type'], row['channel_type'])))
        sizes.append(row['n'])
    fig1, ax1 = plt.subplots(figsize=(4.6, 3.4), constrained_layout=True)
    if sizes:
        ax1.pie(sizes, labels=labels, autopct='%1.0f%%', startangle=90,
                colors=['#2563EB', '#0D9488', '#F59E0B', '#EF4444', '#8B5CF6'])
    else:
        ax1.text(0.5, 0.5, _mpl_ar('لا توجد بيانات'), ha='center', va='center', fontsize=13)
        ax1.axis('off')
    chart_channels = _chart_bytes(fig1)

    # Daily activity (bar)
    days, counts = [], []
    d = start.date()
    while d < end.date():
        days.append(d.strftime('%m-%d'))
        counts.append(logs.filter(timestamp__date=d).count())
        d += timedelta(days=1)
    fig2, ax2 = plt.subplots(figsize=(7.0, 3.0), constrained_layout=True)
    ax2.bar(days, counts, color='#2563EB')
    ax2.set_title(_mpl_ar('النشاط اليومي (أحداث الأمان)'), fontsize=11)
    ax2.spines[['top', 'right']].set_visible(False)
    ax2.tick_params(axis='x', rotation=45, labelsize=7)
    chart_activity = _chart_bytes(fig2)

    # Security severity (barh)
    sev = dict(logs.values('severity').annotate(n=Count('id')).values_list('severity', 'n'))
    fig3, ax3 = plt.subplots(figsize=(4.6, 2.6), constrained_layout=True)
    sev_labels = [_mpl_ar(x) for x in ['معلومة', 'تحذير', 'حرج']]
    vals = [sev.get('INFO', 0), sev.get('WARNING', 0), sev.get('CRITICAL', 0)]
    ax3.barh(sev_labels, vals, color=['#10B981', '#F59E0B', '#EF4444'])
    ax3.set_title(_mpl_ar('الأحداث حسب الخطورة'), fontsize=11)
    ax3.spines[['top', 'right']].set_visible(False)
    chart_security = _chart_bytes(fig3)

    # ---- PDF ----
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=16 * mm,
                            leftMargin=15 * mm, rightMargin=15 * mm)
    title_style = ParagraphStyle('t', fontName=FONT_BOLD, fontSize=17, alignment=2, textColor=BRAND_DARK, spaceAfter=10)
    sub_style = ParagraphStyle('s', fontName=FONT_NORMAL, fontSize=10, alignment=2, textColor=colors.HexColor('#6B7280'))
    head_style = ParagraphStyle('h', fontName=FONT_BOLD, fontSize=12, alignment=2, textColor=BRAND_DARK, spaceBefore=8, spaceAfter=4)
    cell = ParagraphStyle('c', fontName=FONT_NORMAL, fontSize=9, leading=12, alignment=2)

    kpis = [
        ('مستخدم جديد', User.objects.filter(created_at__range=(start, end)).count()),
        ('مرضى جدد', patients.count()),
        ('قنوات جديدة', channels.count()),
        ('سجلات طبية', records.count()),
        ('رسائل القنوات', messages.count()),
        ('أحداث أمنية', logs.count()),
    ]
    kpi_rows = [[Paragraph(ar(k), ParagraphStyle('k', parent=cell, fontName=FONT_BOLD)),
                 Paragraph(str(v), cell)] for k, v in kpis]
    kpi_table = Table(kpi_rows, colWidths=[80 * mm, 80 * mm])
    kpi_table.setStyle(TableStyle([
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [LIGHT_ROW, colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.5, GRID),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    top_users = list(
        logs.exclude(user=None).values('user__full_name')
        .annotate(n=Count('id')).order_by('-n')[:5]
    )

    story = [
        Paragraph(ar('التقرير الشهري للأداء والأمان'), title_style),
        Paragraph(ar(f"الفترة: {start.strftime('%Y-%m')} — SecureMed"), sub_style),
        Spacer(1, 5 * mm),
        Paragraph(ar('مؤشرات الأداء الرئيسية'), head_style),
        kpi_table,
        Paragraph(ar('توزيع القنوات حسب النوع'), head_style),
        Image(chart_channels, width=95 * mm, height=70 * mm),
        Spacer(1, 3 * mm),
        Paragraph(ar('النشاط اليومي'), head_style),
        Image(chart_activity, width=160 * mm, height=68 * mm),
        Spacer(1, 3 * mm),
        Paragraph(ar('ملخص الأمان'), head_style),
        Image(chart_security, width=95 * mm, height=54 * mm),
        Paragraph(ar(
            f"حظر WAF: {logs.filter(event_type='WAF_BLOCKED').count()} | "
            f"محاولات دخول فاشلة: {logs.filter(event_type='LOGIN_FAILED').count()} | "
            f"دخول بيوميتري: {logs.filter(event_type='BIOMETRIC_LOGIN_SUCCESS').count()}"
        ), cell),
        Paragraph(ar('أكثر المستخدمين نشاطاً'), head_style),
        Paragraph(ar(' | '.join(f"{r['user__full_name']}: {r['n']}" for r in top_users) or 'لا توجد بيانات'), cell),
        Paragraph(ar(f"تم التوليد بواسطة {generated_by} — وثيقة سرية"), ParagraphStyle('f', parent=sub_style, alignment=1, spaceBefore=8)),
    ]
    doc.build(story)

    filename = f"SecureMed_Monthly_{start.strftime('%Y-%m')}.pdf"
    return buf.getvalue(), filename, start


def monthly_report_recipients() -> list:
    """Users who should receive scheduled monthly reports (admins + auditors)."""
    return list(
        User.objects.filter(
            is_active=True,
            role__in=['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'AUDITOR'],
        ).exclude(email='')
    )


def send_report_email(to_email: str, month_label: str, filename: str, pdf_bytes: bytes) -> bool:
    """Email the monthly report PDF as an attachment to one recipient."""
    from django.conf import settings as dj_settings
    from django.core.mail import EmailMessage
    from utils.email_service import render_email_html

    html = render_email_html(
        'التقرير الشهري للأداء والأمان',
        f"""
        <p>تحية طيبة،</p>
        <p>تجدون مرفقاً <b>التقرير الشهري للأداء والأمان</b> عن الفترة
        <b>{month_label}</b> لمنصة SecureMed.</p>
        <p>يشمل التقرير مؤشرات الأداء الرئيسية، توزيع القنوات حسب النوع،
        النشاط اليومي، وملخص الأحداث الأمنية حسب الخطورة.</p>
        <p style="color:#6B7280;font-size:12px">
          يمكن أيضاً تحميل التقرير مباشرة من صفحة التحليلات داخل المنصة.
        </p>
        """,
        footer_note='أُرسل هذا التقرير آلياً من منصة SecureMed.',
    )
    import re as _re
    from django.core.mail import EmailMultiAlternatives
    text = _re.sub(r'<[^>]+>', ' ', html)
    try:
        msg = EmailMultiAlternatives(
            subject=f'SecureMed — التقرير الشهري {month_label}',
            body=text,
            from_email=getattr(dj_settings, 'DEFAULT_FROM_EMAIL', 'noreply@securemed.app'),
            to=[to_email],
        )
        msg.attach_alternative(html, 'text/html')
        msg.attach(filename, pdf_bytes, 'application/pdf')
        sent = msg.send(fail_silently=False)
        return sent > 0
    except Exception:  # noqa: BLE001 — email must never break the caller
        import logging
        logging.getLogger('security').error(
            'MONTHLY_REPORT_EMAIL_FAILED to=%s month=%s', to_email, month_label,
            exc_info=True,
        )
        return False
