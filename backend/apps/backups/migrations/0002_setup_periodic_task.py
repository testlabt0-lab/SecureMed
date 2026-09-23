# Generated manually to setup periodic task for backups

from django.db import migrations

def create_periodic_task(apps, schema_editor):
    try:
        from django_celery_beat.models import PeriodicTask, CrontabSchedule
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='2',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*'
        )
        PeriodicTask.objects.update_or_create(
            name='Daily Auto Backup',
            defaults={
                'crontab': schedule,
                'task': 'apps.backups.tasks.run_scheduled_backup',
                'enabled': True
            }
        )
    except Exception as e:
        print(f"Skipping periodic task creation: {e}")

def remove_periodic_task(apps, schema_editor):
    try:
        from django_celery_beat.models import PeriodicTask
        PeriodicTask.objects.filter(name='Daily Auto Backup').delete()
    except Exception as e:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_periodic_task, remove_periodic_task),
    ]
