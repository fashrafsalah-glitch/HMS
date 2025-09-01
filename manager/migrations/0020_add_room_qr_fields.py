# Generated migration for adding QR code fields to Room model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0019_vitalsign_taken_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='qr_code',
            field=models.ImageField(blank=True, null=True, upload_to='qr_codes/'),
        ),
        migrations.AddField(
            model_name='room',
            name='qr_token',
            field=models.CharField(blank=True, max_length=200, null=True, unique=True),
        ),
    ]
