"""
Scheduled reports command
-------------------------
Usage (cron / manual):
    python manage.py send_scheduled_reports --type monthly   # full PDF report
    python manage.py send_scheduled_reports --type weekly    # quick KPI summary
    python manage.py send_scheduled_reports --type monthly --month 2026-07

Suggested crontab (first day of every month at 08:00):
    0 8 1 * *  cd /path/to/backend && python manage.py send_scheduled_reports --type monthly

Weekly (every Sunday at 08:00):
    0 8 * * 0 cd /path/to/backend && python manage.py send_scheduled_reports --type weekly
"""
from datetime import timedelta 

from django .core .management .base import BaseCommand ,CommandError 
from django .utils import timezone 
from django .db .models import Count ,Q 

from apps .accounts .models import User 
from apps .channels .models import Channel ,ChannelMessage 
from apps .patients .models import Patient ,MedicalRecord 
from apps .audit .models import AuditLog 
from apps .audit .utils import log_security_event 
from apps .reports .monthly import (
build_monthly_report ,monthly_report_recipients ,
)
from utils .email_service import (
send_securemed_email ,render_kpi_table ,render_email_html ,
)


class Command (BaseCommand ):
    help ='Email scheduled reports (monthly PDF / weekly KPI summary) to admins and auditors.'

    def add_arguments (self ,parser ):
        parser .add_argument ('--type',choices =['monthly','weekly'],default ='monthly')
        parser .add_argument ('--month',default =None ,help ='YYYY-MM (monthly only, default: current month)')

    def handle (self ,*args ,**options ):
        report_type =options ['type']
        recipients =monthly_report_recipients ()
        if not recipients :
            self .stdout .write (self .style .WARNING ('لا يوجد مستلمون (مدراء/مراجعون) — لم يُرسل شيء'))
            return 

        if report_type =='monthly':
            self ._send_monthly (options ['month'],recipients )
        else :
            self ._send_weekly (recipients )

            # Comment_307
    def _send_monthly (self ,month_str ,recipients ):
        pdf_bytes ,filename ,start =build_monthly_report (month_str ,generated_by ='الجدولة الآلية')
        month_label =start .strftime ('%Y-%m')
        sent ,failed =[],[]
        for user in recipients :
            from apps .reports .monthly import send_report_email 
            ok =send_report_email (user .email ,month_label ,filename ,pdf_bytes )
            (sent if ok else failed ).append (user .email )

        log_security_event (
        user =None ,
        event_type ='SCHEDULED_REPORT_SENT',
        details ={'report':'monthly','month':month_label ,
        'sent':sent ,'failed':failed },
        )
        self .stdout .write (self .style .SUCCESS (
        f'[monthly {month_label }] أُرسل إلى {len (sent )} — فشل: {len (failed )}'
        ))
        if failed :
            self .stdout .write (self .style .WARNING (f'فشل: {", ".join (failed )}'))

            # Comment_308
    def _send_weekly (self ,recipients ):
        now =timezone .now ()
        start =now -timedelta (days =7 )

        logs =AuditLog .objects .filter (timestamp__range =(start ,now ))
        kpis =[
        ('الفترة',f'{start .strftime ("%Y-%m-%d")} → {now .strftime ("%Y-%m-%d")}'),
        ('مرضى جدد',Patient .objects .filter (created_at__range =(start ,now )).count ()),
        ('قنوات جديدة',Channel .objects .filter (created_at__range =(start ,now )).count ()),
        ('سجلات طبية',MedicalRecord .objects .filter (created_at__range =(start ,now )).count ()),
        ('رسائل القنوات',ChannelMessage .objects .filter (created_at__range =(start ,now )).count ()),
        ('أحداث أمنية',logs .count ()),
        ('حظر WAF',logs .filter (event_type ='WAF_BLOCKED').count ()),
        ('دخول ناجح',logs .filter (event_type ='LOGIN_SUCCESS').count ()),
        ]
        body =render_kpi_table (kpis )
        html =render_email_html (
        'الملخص الأسبوعي — منصة SecureMed',
        '<p>تحية طيبة،</p><p>أبرز مؤشرات الأداء والأمان خلال الأسبوع الماضي:</p>'
        +body ,
        footer_note ='أُرسل هذا الملخص آلياً كل أسبوع من منصة SecureMed.',
        )

        sent ,failed =[],[]
        for user in recipients :
            ok =send_securemed_email (
            to_email =user .email ,
            subject ='SecureMed — الملخص الأسبوعي للأداء والأمان',
            title ='الملخص الأسبوعي',
            body_html =body ,
            footer_note ='أُرسل هذا الملخص آلياً كل أسبوع من منصة SecureMed.',
            )
            (sent if ok else failed ).append (user .email )

        log_security_event (
        user =None ,
        event_type ='SCHEDULED_REPORT_SENT',
        details ={'report':'weekly','sent':sent ,'failed':failed },
        )
        self .stdout .write (self .style .SUCCESS (
        f'[weekly] أُرسل إلى {len (sent )} — فشل: {len (failed )}'
        ))
