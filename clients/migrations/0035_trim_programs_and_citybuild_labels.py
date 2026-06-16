from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0034_split_capsa_and_citybuild_academy'),
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
                    ('general', 'General Employment Assistance'),
                ],
                default='general',
                max_length=20,
            ),
        ),
        migrations.AlterModelOptions(
            name='citybuildfilechecklist',
            options={
                'verbose_name': 'City Build file checklist',
                'verbose_name_plural': 'City Build file checklists',
            },
        ),
    ]
