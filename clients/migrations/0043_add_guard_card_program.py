# Re-add Security Guard Card Training as a program choice.
# Records folded into 'general' by 0040 are not restored; this only reopens the option.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0042_partner_referral_ingest'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='training_interest',
            field=models.CharField(
                choices=[
                    ('capsa', 'CAPSA'),
                    ('citybuild', 'City Build'),
                    ('pit_stop', 'Pit Stop'),
                    ('guard_card', 'Security Guard Card Training'),
                    ('general', 'General Employment Assistance'),
                ],
                default='general',
                max_length=20,
            ),
        ),
    ]
