from django.core.management.base import BaseCommand
from apps.accounts.models import User
import os

class Command(BaseCommand):
    help = 'Creates an initial admin user if none exists'

    def handle(self, *args, **options):
        admin_email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@securemed.app')
        admin_password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
        
        if not User.objects.filter(email=admin_email).exists():
            User.objects.create_superuser(
                email=admin_email,
                password=admin_password,
                role=User.Role.ADMIN
            )
            self.stdout.write(self.style.SUCCESS(f'Created initial admin user: {admin_email}'))
        else:
            self.stdout.write(self.style.WARNING(f'Admin user {admin_email} already exists'))
