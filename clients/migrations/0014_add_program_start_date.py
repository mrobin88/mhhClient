# Generated migration for adding program_start_date field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0013_alter_worksite_typical_end_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='program_start_date',
            field=models.DateField(blank=True, help_text='Date when client started their program', null=True),
        ),
    ]
