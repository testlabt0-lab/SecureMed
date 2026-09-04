"""
Celery configuration for SecureMed.
Handles background tasks: email notifications, scheduled backups,
JWT token cleanup, monthly reports, appointment reminders.
"""
import os 
from celery import Celery 
from celery .schedules import crontab 

os .environ .setdefault ('DJANGO_SETTINGS_MODULE','config.settings')

app =Celery ('securemed')

# Comment_426
app .config_from_object ('django.conf:settings',namespace ='CELERY')

# Comment_427
app .autodiscover_tasks ()


# Comment_428
app .conf .beat_schedule ={
# Comment_429
'appointment-reminders-24h':{
'task':'apps.appointments.tasks.send_appointment_reminders',
'schedule':crontab (minute =0 ,hour ='*'),# Comment_430
'kwargs':{'hours_before':24 },
},
# Comment_431
'appointment-reminders-1h':{
'task':'apps.appointments.tasks.send_appointment_reminders',
'schedule':crontab (minute =0 ,hour ='*'),
'kwargs':{'hours_before':1 },
},
# Comment_432
'daily-backup':{
'task':'apps.backups.tasks.run_scheduled_backup',
'schedule':crontab (minute =0 ,hour =2 ),
},
# Comment_433
'cleanup-expired-tokens':{
'task':'apps.accounts.tasks.cleanup_expired_tokens',
'schedule':crontab (minute =0 ,hour =3 ),
},
# Comment_434
'monthly-report':{
'task':'apps.reports.tasks.generate_monthly_report',
'schedule':crontab (minute =0 ,hour =6 ,day_of_month =1 ),
},
# Comment_435
'flush-notification-emails':{
'task':'apps.notifications.tasks.flush_pending_emails',
'schedule':crontab (minute ='*/5'),
},
# Comment_436
'security-digest':{
'task':'apps.audit.tasks.send_security_digest',
'schedule':crontab (minute =0 ,hour =8 ),
},
}

app .conf .timezone ='Asia/Riyadh'
