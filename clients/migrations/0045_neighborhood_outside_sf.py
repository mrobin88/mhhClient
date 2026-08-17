# Clients outside San Francisco had no honest answer for the area question and
# were picking "Other San Francisco Area". Adds a real option plus a free-text box.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0044_class_confirmation_sms_purpose'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='neighborhood_other',
            field=models.CharField(
                blank=True,
                null=True,
                max_length=100,
                help_text='Neighborhood or city typed in when the list does not cover it.',
            ),
        ),
        migrations.AlterField(
            model_name='client',
            name='neighborhood',
            field=models.CharField(
                choices=[
                    ('mission', 'Mission District'),
                    ('soma', 'South of Market (SoMa)'),
                    ('bayview', 'Bayview-Hunters Point'),
                    ('tenderloin', 'Tenderloin'),
                    ('western', 'Western Addition'),
                    ('other', 'Other San Francisco Area'),
                    ('outside_sf', 'Outside San Francisco'),
                ],
                default='other',
                max_length=20,
            ),
        ),
    ]
