from django.apps import AppConfig

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'
    verbose_name = 'الإشعارات'

    def ready(self):
        # استيراد ملف الإشارات عند بدء تشغيل التطبيق
        import apps.notifications.signals
