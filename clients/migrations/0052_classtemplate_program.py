# Class templates belong to a client program (City Build, Pit Stop, etc.).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0051_citybuild_stage_and_class_update_sms'),
    ]

    operations = [
        migrations.AddField(
            model_name='classtemplate',
            name='program',
            field=models.CharField(
                choices=[
                    ('capsa', 'CAPSA'),
                    ('citybuild', 'City Build'),
                    ('pit_stop', 'Pit Stop'),
                    ('guard_card', 'Security Guard Card Training'),
                    ('general', 'General Employment Assistance'),
                ],
                db_index=True,
                default='general',
                help_text='Which client program this class belongs to. City Build info sessions must be City Build.',
                max_length=20,
            ),
        ),
    ]
