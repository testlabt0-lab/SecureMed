"""
Audit chain verification
------------------------
Recomputes the HMAC of every audit row and re-walks the previous_hash links, so
tampering with the audit trail — editing a row, deleting one out of the middle,
inserting a forged one — becomes visible instead of theoretical.

Usage:
    python manage.py verify_audit_chain
    python manage.py verify_audit_chain --days 7
    python manage.py verify_audit_chain --since 2026-09-01 --json

Suggested crontab (daily at 03:00, alert on non-zero exit):
    0 3 * * * cd /path/to/backend && python manage.py verify_audit_chain --days 2

Exit code is 1 when any problem is found, so a scheduler or CI job can treat it as
a failure without parsing the output.
"""
import json as json_lib
from datetime import timedelta

from django .core .management .base import BaseCommand ,CommandError
from django .utils import timezone
from django .utils .dateparse import parse_datetime ,parse_date

from apps .audit .models import AuditLog


class Command (BaseCommand ):
    help ='Verify the integrity of the audit log hash chain.'

    def add_arguments (self ,parser ):
        parser .add_argument ('--days',type =int ,default =None ,
        help ='Only verify rows from the last N days (faster on a large table).')
        parser .add_argument ('--since',default =None ,
        help ='Only verify rows at or after this date/datetime (YYYY-MM-DD).')
        parser .add_argument ('--limit',type =int ,default =None ,
        help ='Stop after N rows.')
        parser .add_argument ('--json',action ='store_true',dest ='as_json',
        help ='Emit the raw result dict instead of a readable report.')

    def handle (self ,*args ,**options ):
        since =self ._resolve_since (options )
        result =AuditLog .verify_chain (since =since ,limit =options ['limit'])

        if options ['as_json']:
            self .stdout .write (json_lib .dumps (result ,ensure_ascii =False ,indent =2 ))
        else :
            self ._report (result ,since )

        if not result ['ok']:
            # Non-zero exit is the whole point when this runs unattended.
            raise SystemExit (1 )

    def _resolve_since (self ,options ):
        if options ['days']is not None and options ['since']:
            raise CommandError ('استخدم --days أو --since، لا كليهما')
        if options ['days']is not None :
            return timezone .now ()-timedelta (days =options ['days'])
        if options ['since']:
            parsed =parse_datetime (options ['since'])
            if parsed is None :
                day =parse_date (options ['since'])
                if day is None :
                    raise CommandError (f"تاريخ غير مفهوم: {options ['since']}")
                parsed =timezone .datetime .combine (day ,timezone .datetime .min .time ())
            if timezone .is_naive (parsed ):
                parsed =timezone .make_aware (parsed )
            return parsed
        return None

    def _report (self ,result ,since ):
        scope ='كل السجلات'if since is None else f'من {since .isoformat ()}'
        self .stdout .write (f'نطاق التحقق: {scope }')
        self .stdout .write (f"عدد السجلات المفحوصة: {result ['checked']}")
        self .stdout .write (f"موقّعة بالمفتاح الحالي: {result ['signed']}")

        if result ['legacy']:
            self .stdout .write (self .style .WARNING (
            f"موقّعة بالخوارزمية القديمة غير المفتاحية: {result ['legacy']} "
            '(سليمة لكنها قابلة لإعادة الحساب — لا تُعتمد كدليل)'
            ))
        if result ['unsigned']:
            self .stdout .write (self .style .WARNING (
            f"غير موقّعة إطلاقاً: {result ['unsigned']} "
            '(كُتبت قبل تفعيل التوقيع)'
            ))

        if result ['ok']:
            self .stdout .write (self .style .SUCCESS ('سلسلة التدقيق سليمة — لا يوجد تلاعب مكتشف'))
            return

        self .stdout .write (self .style .ERROR (
        f"مشاكل مكتشفة: {len (result ['problems'])}"
        ))
        for problem in result ['problems'][:50 ]:
            if problem ['error']=='signature_mismatch':
                detail ='التوقيع لا يطابق محتوى السجل (تم تعديل السجل)'
            else :
                detail =(f"الحلقة مكسورة — المتوقع {problem .get ('expected_previous')} "
                f"والموجود {problem .get ('found_previous')} (حُذف سجل أو أُدرج سجل مزيّف)")
            self .stdout .write (self .style .ERROR (
            f"  - {problem ['timestamp']} | {problem ['id']} | {detail }"
            ))
        if len (result ['problems'])>50 :
            self .stdout .write (self .style .ERROR (
            f"  ... و{len (result ['problems'])-50 } مشكلة أخرى"
            ))
