from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0035_trim_programs_and_citybuild_labels'),
    ]

    operations = [
        migrations.AddField(
            model_name='workeraccount',
            name='long_term_career_goals',
            field=models.TextField(blank=True, help_text='Worker-entered long-term career goals.'),
        ),
        migrations.AddField(
            model_name='workeraccount',
            name='short_profile',
            field=models.TextField(blank=True, help_text='Short self-written profile visible in the worker portal.'),
        ),
        migrations.CreateModel(
            name='WorkerDailyFeedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feedback_date', models.DateField(default=django.utils.timezone.localdate)),
                ('feedback_text', models.TextField(help_text='Daily worker feedback.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('worker_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='daily_feedback_entries', to='clients.workeraccount')),
            ],
            options={
                'verbose_name': 'Worker Daily Feedback',
                'verbose_name_plural': 'Worker Daily Feedback',
                'ordering': ['-feedback_date', '-updated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='workerdailyfeedback',
            index=models.Index(fields=['worker_account', 'feedback_date'], name='clients_wor_worker__6eeea4_idx'),
        ),
        migrations.AddConstraint(
            model_name='workerdailyfeedback',
            constraint=models.UniqueConstraint(fields=('worker_account', 'feedback_date'), name='unique_worker_feedback_per_day'),
        ),
    ]
