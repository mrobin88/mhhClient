# Generated manually on 2025-10-16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0008_auto_20251008_1545'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pitstopapplication',
            name='employment_desired',
            field=models.JSONField(
                default=list,
                help_text='Employment types desired: ["full_time", "part_time", "relief_list"] - can select multiple'
            ),
        ),
    ]

