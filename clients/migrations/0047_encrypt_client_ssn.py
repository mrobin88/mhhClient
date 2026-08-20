import clients.encrypted_fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('clients', '0046_pitstop_review_pipeline'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='ssn',
            field=clients.encrypted_fields.EncryptedSSNField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='ssn_key_id',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
        migrations.AddField(
            model_name='client',
            name='ssn_last4',
            field=models.CharField(blank=True, db_index=True, default='', max_length=4),
        ),
    ]
