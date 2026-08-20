from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20250925_2315'),
    ]

    operations = [
        migrations.AddField(
            model_name='staffuser',
            name='accent_color',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Staff dashboard accent as #RRGGBB so the UI can match their desk.',
                max_length=7,
            ),
        ),
    ]
