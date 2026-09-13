"""
Management command to populate blind index fields for existing patients.
Can be run via: python manage.py populate_blind_indexes
"""
from django.core.management.base import BaseCommand
from apps.patients.models import Patient
from apps.security.blind_index import compute_blind_index, compute_search_tokens


class Command(BaseCommand):
    help = 'Populate blind indexes for encrypted patient records'

    def handle(self, *args, **options):
        total = Patient.objects.count()
        self.stdout.write(f'Populating blind indexes for {total} patients...')
        updated = 0
        for patient in Patient.objects.all():
            changed = False
            try:
                name = patient.full_name
                if name and not patient.name_bindex:
                    patient.name_bindex = compute_search_tokens(name)
                    changed = True
            except Exception:
                pass

            try:
                nid = patient.national_id
                if nid and not patient.national_id_bindex:
                    patient.national_id_bindex = compute_blind_index(nid)
                    changed = True
            except Exception:
                pass

            try:
                phone = patient.phone
                if phone and not patient.phone_bindex:
                    patient.phone_bindex = compute_blind_index(phone)
                    changed = True
            except Exception:
                pass

            if changed:
                patient.save(update_fields=['name_bindex', 'national_id_bindex', 'phone_bindex'])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated} / {total} patient blind indexes.'))
