from django.db import migrations, models


def merge_citybuild_pro_into_capsa(apps, schema_editor):
    Client = apps.get_model('clients', 'Client')
    Client.objects.filter(training_interest='citybuild_pro').update(training_interest='citybuild')


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0032_citybuild_file_checklist_proxy'),
    ]

    operations = [
        migrations.RunPython(merge_citybuild_pro_into_capsa, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='client',
            name='training_interest',
            field=models.CharField(
                choices=[
                    ('citybuild', 'CAPSA'),
                    ('security', 'Security Guard Card Program'),
                    ('construction', 'Construction On Ramp'),
                    ('pit_stop', 'Pit Stop Program'),
                    ('general', 'General Employment Assistance'),
                    ('other', 'Other training'),
                ],
                default='general',
                max_length=20,
            ),
        ),
        migrations.AlterModelOptions(
            name='citybuildfilechecklist',
            options={
                'verbose_name': 'CAPSA file checklist',
                'verbose_name_plural': 'CAPSA file checklists',
            },
        ),
    ]
