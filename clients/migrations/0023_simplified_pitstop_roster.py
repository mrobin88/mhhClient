from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0022_worker_notes_timeoff_geo_flags'),
    ]

    operations = [
        migrations.AddField(
            model_name='workeraccount',
            name='worker_status',
            field=models.CharField(
                choices=[
                    ('applicant', 'Applicant'),
                    ('active', 'Active Worker'),
                    ('inactive', 'Inactive'),
                ],
                default='applicant',
                help_text='Roster status: applicant, active worker, or inactive.',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='workeraccount',
            name='is_available',
            field=models.BooleanField(
                default=True,
                help_text='Simple roster availability toggle. Replaces time-slot availability.',
            ),
        ),
        migrations.AddField(
            model_name='workeraccount',
            name='follow_up_notes',
            field=models.TextField(
                blank=True,
                help_text='Roster notes / follow-up history visible to staff.',
            ),
        ),
        migrations.AddField(
            model_name='workertimepunch',
            name='assignment',
            field=models.ForeignKey(
                blank=True,
                help_text='Work assignment this punch belongs to. New punches should always set this.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='time_punches',
                to='clients.workassignment',
            ),
        ),
        migrations.AddIndex(
            model_name='workertimepunch',
            index=models.Index(fields=['assignment', 'clock_out_at'], name='clients_wor_assignm_53725a_idx'),
        ),
    ]
