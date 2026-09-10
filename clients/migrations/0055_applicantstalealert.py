# One Teams notice per applicant after 3 weeks with no outreach.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0054_pitstop_application_paper_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicantStaleAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('applied_for', models.CharField(max_length=200)),
                ('days_stale', models.PositiveIntegerField()),
                (
                    'channel',
                    models.CharField(
                        blank=True,
                        choices=[
                            ('webhook', 'Teams webhook'),
                            ('graph', 'Teams Graph'),
                            ('email', 'Teams channel email'),
                        ],
                        max_length=20,
                    ),
                ),
                ('notified_at', models.DateTimeField(auto_now_add=True)),
                (
                    'client',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='stale_applicant_alert',
                        to='clients.client',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Applicant stale alert',
                'verbose_name_plural': 'Applicant stale alerts',
                'ordering': ['-notified_at'],
            },
        ),
    ]
