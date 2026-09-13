# Generated for SecureMed - Blind Indexing for Encrypted Patient Search

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0004_rename_patient_basin_created_idx_patients_pa_basin_i_0a03a3_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='name_bindex',
            field=models.TextField(blank=True, default='', verbose_name='فهرس الاسم الأعمى'),
        ),
        migrations.AddField(
            model_name='patient',
            name='national_id_bindex',
            field=models.CharField(blank=True, db_index=True, default='', max_length=64, verbose_name='فهرس الهوية الأعمى'),
        ),
        migrations.AddField(
            model_name='patient',
            name='phone_bindex',
            field=models.CharField(blank=True, db_index=True, default='', max_length=64, verbose_name='فهرس الهاتف الأعمى'),
        ),
        migrations.AddIndex(
            model_name='patient',
            index=models.Index(fields=['national_id_bindex'], name='patients_pa_nid_bidx'),
        ),
        migrations.AddIndex(
            model_name='patient',
            index=models.Index(fields=['phone_bindex'], name='patients_pa_phone_bidx'),
        ),
    ]
