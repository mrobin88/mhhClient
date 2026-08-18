# Pit Stop applications were reviewed on paper. These fields move that triage
# into the admin so staff have one place to look.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0045_neighborhood_outside_sf'),
    ]

    operations = [
        migrations.AddField(
            model_name='pitstopapplication',
            name='review_status',
            field=models.CharField(
                choices=[
                    ('new', 'New - needs review'),
                    ('interviewed', 'Interviewed'),
                    ('maybe', 'Maybe'),
                    ('moving_forward', 'Moving forward'),
                    ('not_moving_forward', 'Not moving forward'),
                ],
                db_index=True,
                default='new',
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='pitstopapplication',
            name='interviewed_on',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='pitstopapplication',
            name='review_notes',
            field=models.TextField(
                blank=True,
                default='',
                help_text='What used to get written on the paper application.',
            ),
        ),
        migrations.AddField(
            model_name='pitstopapplication',
            name='reviewed_by',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
        migrations.AddField(
            model_name='pitstopapplication',
            name='review_updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='pitstopapplication',
            name='employment_history',
            field=models.JSONField(
                default=list,
                help_text='Retired. Older applications may still hold a last-job entry.',
            ),
        ),
    ]
