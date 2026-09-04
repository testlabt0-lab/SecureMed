from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from apps.accounts.models import User

class Command(BaseCommand):
    help = 'Sets up default roles (Groups) and their initial permissions'

    def handle(self, *args, **options):
        roles = [choice[0] for choice in User.Role.choices]
        
        for role in roles:
            group, created = Group.objects.get_or_create(name=role)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created group for role: {role}'))
            else:
                self.stdout.write(self.style.WARNING(f'Group for role {role} already exists'))

        self.stdout.write(self.style.SUCCESS('Successfully setup roles.'))
