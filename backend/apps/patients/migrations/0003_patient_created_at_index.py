# Generated for the index additions on apps.patients.models.Patient.
#
# Patients are listed in -created_at order (apps.patients.views.PatientViewSet
# uses it as the default ordering, and the /api/v1/patients/ list endpoint is
# the one the basin-scoped dashboard pages hit on every page load). Without
# these indexes Postgres runs a seq scan + in-memory sort once a basin has
# more than a few hundred patients, which is exactly when the dashboard starts
# feeling slow under real traffic.
#
# The basin_id+created_at compound is the one the basin-scoped filter turns
# into, so it covers the most common WHERE+ORDER BY combination in one access
# path. The single-column -created_at index covers the unscoped (admin) view.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0002_patient_user'),
        ('basins', '__latest__'),
    ]

    operations = [
        migrations.AlterField(
            model_name='patient',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=None),
        ),
        migrations.AddIndex(
            model_name='patient',
            index=models.Index(fields=['basin', '-created_at'], name='patient_basin_created_idx'),
        ),
        migrations.AddIndex(
            model_name='patient',
            index=models.Index(fields=['-created_at'], name='patient_created_idx'),
        ),
    ]
