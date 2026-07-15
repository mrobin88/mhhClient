from django.db import migrations, models


def fold_guard_card_into_general(apps, schema_editor):
    Client = apps.get_model('clients', 'Client')
    Client.objects.filter(training_interest='guard_card').update(training_interest='general')


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0039_classes_and_rosters'),
    ]

    operations = [
        migrations.RunPython(fold_guard_card_into_general, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='client',
            name='training_interest',
            field=models.CharField(
                choices=[
                    ('capsa', 'CAPSA'),
                    ('citybuild', 'City Build'),
                    ('pit_stop', 'Pit Stop'),
                    ('general', 'General Employment Assistance'),
                ],
                default='general',
                max_length=20,
            ),
        ),
        migrations.RemoveIndex(
            model_name='guardcardenrollment',
            name='clients_gua_next_fo_d9529a_idx',
        ),
        migrations.RemoveIndex(
            model_name='guardcardenrollment',
            name='clients_gua_barrier_9a90b6_idx',
        ),
        migrations.RemoveField(
            model_name='guardcardenrollment',
            name='client',
        ),
        migrations.DeleteModel(
            name='GuardCardEnrollment',
        ),
    ]
