from django.db import migrations, models

import clients.models_extensions


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0029_casenote_note_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='workertimepunch',
            name='clock_in_location_label',
            field=models.CharField(
                blank=True,
                help_text='Approximate address or cross streets at clock-in (display only).',
                max_length=300,
            ),
        ),
        migrations.AddField(
            model_name='workertimepunch',
            name='clock_out_location_label',
            field=models.CharField(
                blank=True,
                help_text='Approximate address or cross streets at clock-out (display only).',
                max_length=300,
            ),
        ),
        migrations.AddField(
            model_name='workertimepunch',
            name='clock_in_map_image',
            field=models.ImageField(
                blank=True,
                help_text='Static map snapshot at clock-in (visual reference only).',
                null=True,
                upload_to=clients.models_extensions.worker_punch_map_upload_to,
            ),
        ),
        migrations.AddField(
            model_name='workertimepunch',
            name='clock_out_map_image',
            field=models.ImageField(
                blank=True,
                help_text='Static map snapshot at clock-out (visual reference only).',
                null=True,
                upload_to=clients.models_extensions.worker_punch_map_upload_to,
            ),
        ),
    ]
