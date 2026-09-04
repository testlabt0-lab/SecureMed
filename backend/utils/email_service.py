"""
SecureMed Email Service
=======================
Central email sending with branded Arabic RTL HTML templates.

Backend selection (settings.py / env):
- SMTP          → when EMAIL_HOST is configured (production)
- filebased     → writes real .eml files to backend/logs/emails/ (dev/demo,
                  lets you verify the actual message content without SMTP)
- console       → fallback (prints to stdout)

Every send is fail-safe: errors are logged, never raised, so a broken
SMTP config must not break API requests.
"""
from __future__ import annotations 

import logging 
import traceback 
from datetime import datetime 

from django .conf import settings 
from django .core .mail import EmailMultiAlternatives 

logger =logging .getLogger ('security')


# Comment_601
# Comment_602
# Comment_603
def render_email_html (title :str ,body_html :str ,footer_note :str ='')->str :
    """Wrap email content in the SecureMed branded RTL template."""
    year =datetime .now ().year 
    note =f'<p style="color:#6B7280;font-size:12px;margin:4px 0 0">{footer_note }</p>'if footer_note else ''
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><title>{title }</title></head>
<body style="margin:0;padding:0;background:#F3F4F6;font-family:'Segoe UI',Tahoma,Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F3F4F6;padding:24px 0;">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08);">
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#2563EB,#0D9488);padding:22px 28px;text-align:center;">
            <div style="color:#ffffff;font-size:22px;font-weight:bold;letter-spacing:.5px;">
              &#9877; SecureMed
            </div>
            <div style="color:rgba(255,255,255,.85);font-size:13px;margin-top:4px;">
              منصة إدارة الحالات الطبية الآمنة
            </div>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:28px 30px;color:#1F2937;font-size:14px;line-height:1.9;">
            <h2 style="color:#1E40AF;font-size:18px;margin:0 0 14px;">{title }</h2>
            {body_html }
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background:#F9FAFB;padding:16px 28px;border-top:1px solid #E5E7EB;text-align:center;">
            {note }
            <p style="color:#9CA3AF;font-size:11px;margin:6px 0 0;">
              &copy; {year } SecureMed — هذه الرسالة أُرسلت آلياً، لا تردّ عليها.
              <br>إذا لم تتوقع وصول هذه الرسالة يمكنك تجاهلها بأمان.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def render_kpi_table (rows :list [tuple [str ,str ]])->str :
    """Render a simple KPI table (label → value) as branded HTML."""
    trs =''.join (
    f'<tr>'
    f'<td style="padding:8px 14px;border-bottom:1px solid #EFF6FF;font-weight:bold;color:#1E40AF;">{k }</td>'
    f'<td style="padding:8px 14px;border-bottom:1px solid #EFF6FF;">{v }</td>'
    f'</tr>'
    for k ,v in rows 
    )
    return (
    '<table width="100%" cellpadding="0" cellspacing="0" '
    'style="border:1px solid #BFDBFE;border-radius:8px;overflow:hidden;border-collapse:collapse;">'
    f'{trs }</table>'
    )


    # Comment_604
    # Comment_605
    # Comment_606
def send_securemed_email (
to_email :str |list [str ],
subject :str ,
title :str ,
body_html :str ,
footer_note :str ='',
)->bool :
    """
    Send one branded email. Returns True on success, False otherwise.
    Never raises — callers can treat the return value as the delivery flag.
    """
    if isinstance (to_email ,str ):
        to_email =[to_email ]
    to_email =[e for e in to_email if e ]
    if not to_email :
        return False 

    html =render_email_html (title ,body_html ,footer_note )
    # Comment_607
    import re 
    text =re .sub (r'<[^>]+>',' ',html )
    text =re .sub (r'\s+',' ',text ).strip ()

    try :
    # Comment_608
        backend =getattr (settings ,'EMAIL_BACKEND','')
        file_path =getattr (settings ,'EMAIL_FILE_PATH',None )
        if 'filebased'in backend and file_path :
            import os 
            os .makedirs (str (file_path ),exist_ok =True )

        msg =EmailMultiAlternatives (
        subject =subject ,
        body =text ,
        from_email =getattr (settings ,'DEFAULT_FROM_EMAIL','noreply@securemed.app'),
        to =to_email ,
        )
        msg .attach_alternative (html ,'text/html')
        sent =msg .send (fail_silently =False )
        logger .info ('EMAIL_SENT to=%s subject=%r sent=%s',to_email ,subject ,sent )
        return sent >0 
    except Exception as exc :# Comment_609
        logger .error (
        'EMAIL_FAILED to=%s subject=%r error=%s\n%s',
        to_email ,subject ,exc ,traceback .format_exc (),
        )
        return False 


def send_notification_email (user ,notification )->bool :
    """Email an in-app Notification instance to its recipient."""
    if not getattr (user ,'email',''):
        return False 
    color ={
    'LOW':'#6B7280','MEDIUM':'#2563EB',
    'HIGH':'#D97706','CRITICAL':'#DC2626',
    }.get (notification .priority ,'#2563EB')
    body =f"""
      <p style="margin:0 0 10px">
        <span style="background:{color }1A;color:{color };font-size:12px;
              padding:2px 10px;border-radius:999px;font-weight:bold;">
          {notification .get_priority_display ()}
        </span>
      </p>
      <p style="font-size:15px;font-weight:bold;margin:0 0 6px;">{notification .title }</p>
      <p style="margin:0;color:#374151;">{notification .message }</p>
      <p style="margin:14px 0 0">
        <a href="#" style="color:#2563EB;text-decoration:none;font-size:13px;">
          افتح مركز الإشعارات في المنصة لعرض التفاصيل
        </a>
      </p>"""
    return send_securemed_email (
    to_email =user .email ,
    subject =f'SecureMed — {notification .title }',
    title ='لديك إشعار جديد في منصة SecureMed',
    body_html =body ,
    footer_note ='يمكنك ضبط تفضيلات البريد من مركز الإشعارات داخل المنصة.',
    )
