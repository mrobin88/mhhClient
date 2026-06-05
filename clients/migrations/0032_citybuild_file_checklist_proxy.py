from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0031_citybuild_docs'),
    ]

    operations = [
        migrations.CreateModel(
            name='CityBuildFileChecklist',
            fields=[],
            options={
                'verbose_name': 'CityBuild file checklist',
                'verbose_name_plural': 'CityBuild file checklists',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('clients.client',),
        ),
    ]
