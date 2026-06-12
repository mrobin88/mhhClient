from django.db import migrations, models


def move_mislabeled_capsa_clients(apps, schema_editor):
    """
    Intake briefly mapped CAPSA to citybuild; re-tag those records as capsa.

    City Build Academy (checklist) keeps training_interest=citybuild.
    """
    Client = apps.get_model('clients', 'Client')
    Client.objects.filter(training_interest='citybuild').update(training_interest='capsa')


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0033_remove_citybuild_pro'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='training_interest',
            field=models.CharField(
                choices=[
                    ('citybuild', 'City Build Academy'),
                    ('capsa', 'CAPSA'),
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
        migrations.RunPython(move_mislabeled_capsa_clients, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name='citybuildfilechecklist',
            options={
                'verbose_name': 'City Build Academy file checklist',
                'verbose_name_plural': 'City Build Academy file checklists',
            },
        ),
    ]
