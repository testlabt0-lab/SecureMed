"""Rebuild biometric authentication on public-key credentials.

Additive and widening only — no column is dropped, so this migration is safe to
apply to a populated database and reverses cleanly.

  * BiometricProfile.credential_id / .sign_count are new: the WebAuthn rawId and
    the authenticatorData signature counter used for clone detection.
  * BiometricProfile.biometric_hash / .salt become optional. They held a salted
    hash of a client-supplied "biometric template" that was compared on every
    login — i.e. a shared secret the user can never rotate. The new flow verifies
    a signature instead and writes nothing to these columns. Existing values are
    left in place; `manage.py rotate_encryption_key` still re-encrypts them.
  * BiometricChallenge.profile binds a challenge to the exact enrolled device.
    Previously a challenge was bound to the user only, so a credential enrolled
    on one device could answer a challenge issued for another.
  * BiometricChallenge.expected_response becomes optional; the server no longer
    stores an expected answer at all.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_alter_user_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='biometricprofile',
            name='credential_id',
            field=models.TextField(blank=True, default='', verbose_name='معرف بيانات الاعتماد'),
        ),
        migrations.AddField(
            model_name='biometricprofile',
            name='sign_count',
            field=models.PositiveBigIntegerField(default=0, verbose_name='عدّاد التوقيع'),
        ),
        migrations.AlterField(
            model_name='biometricprofile',
            name='biometric_hash',
            field=models.TextField(blank=True, default='', verbose_name='الهاش البيوميتري المشفر'),
        ),
        migrations.AlterField(
            model_name='biometricprofile',
            name='salt',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='الملح'),
        ),
        migrations.AddField(
            model_name='biometricchallenge',
            name='profile',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='challenges',
                to='accounts.biometricprofile',
            ),
        ),
        migrations.AlterField(
            model_name='biometricchallenge',
            name='expected_response',
            field=models.TextField(blank=True, default='', verbose_name='الرد المتوقع المشفر'),
        ),
    ]
