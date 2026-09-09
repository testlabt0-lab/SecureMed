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

# Use Django settings for Celery config (CELERY_* prefix)
app .config_from_object ('django.conf:settings',namespace ='CELERY')

# Auto-discover tasks in installed apps
app .autodiscover_tasks ()


# ─── Periodic Tasks (beat schedule) ───────────────────────────────────────────
app .conf .beat_schedule ={
# Send appointment reminders 24h before
'appointment-reminders-24h':{
'task':'apps.appointments.tasks.send_appointment_reminders',
'schedule':crontab (minute =0 ,hour ='*'),# every hour
'kwargs':{'hours_before':24 },
},
# Send appointment reminders 1h before
'appointment-reminders-1h':{
'task':'apps.appointments.tasks.send_appointment_reminders',
'schedule':crontab (minute =0 ,hour ='*'),
'kwargs':{'hours_before':1 },
},
# Daily database-only backup at 2 AM — small enough for the Telegram
# 50 MB document channel, covers the data that changes every day
'daily-backup':{
'task':'apps.backups.tasks.run_scheduled_backup',
'schedule':crontab (minute =0 ,hour =2 ),
'kwargs':{'scope':'DATABASE' },
},
# Weekly full archive (media included) — Friday 3 AM
'weekly-full-backup':{
'task':'apps.backups.tasks.run_scheduled_backup',
'schedule':crontab (minute =0 ,hour =3 ,day_of_week ='friday' ),
'kwargs':{'scope':'FULL' },
},
# Cleanup expired JWT tokens from blacklist daily at 3 AM
'cleanup-expired-tokens':{
'task':'apps.accounts.tasks.cleanup_expired_tokens',
'schedule':crontab (minute =0 ,hour =3 ),
},
# Generate monthly report on the 1st of each month at 6 AM
'monthly-report':{
'task':'apps.reports.tasks.generate_monthly_report',
'schedule':crontab (minute =0 ,hour =6 ,day_of_month =1 ),
},
'daily-summary-report':{
'task':'apps.reports.tasks.generate_daily_summary',
'schedule':crontab (minute =50 ,hour =23 ),
},
# Send pending email notifications every 5 minutes
'flush-notification-emails':{
'task':'apps.notifications.tasks.flush_pending_emails',
'schedule':crontab (minute ='*/5'),
},
# Security event digest — daily at 8 AM
'security-digest':{
'task':'apps.audit.tasks.send_security_digest',
'schedule':crontab (minute =0 ,hour =8 ),
},
# Audit hash-chain tamper check — daily at 4 AM, alerts on problems
'verify-audit-chain':{
'task':'apps.audit.tasks.verify_audit_chain_task',
'schedule':crontab (minute =0 ,hour =4 ),
'kwargs':{'days':2 },
},
# Expire stale blocklist rows + untrust long-idle devices — weekly
'cleanup-blocklists':{
'task':'apps.security.tasks.cleanup_blocklists_task',
'schedule':crontab (minute =30 ,hour =5 ,day_of_week =0 ),
},
# Pending-device approvals digest — daily 9 AM (catches pushes Telegram missed)
'pending-devices-digest':{
'task':'apps.security.tasks.send_pending_devices_digest_task',
'schedule':crontab (minute =0 ,hour =9 ),
},
'check-pharmacy-inventory':{
'task':'apps.pharmacy.tasks.check_pharmacy_inventory',
'schedule':crontab (minute =0 ,hour =7 ),
},
}

app .conf .timezone ='Asia/Riyadh'
