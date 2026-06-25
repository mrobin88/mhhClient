from django.db import migrations, models
import django.db.models.deletion


def mark_existing_worker_accounts(apps, schema_editor):
    Client = apps.get_model('clients', 'Client')
    WorkerAccount = apps.get_model('clients', 'WorkerAccount')
    worker_client_ids = WorkerAccount.objects.values_list('client_id', flat=True)
    Client.objects.filter(pk__in=worker_client_ids).update(pit_stop_stage='worker')


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0036_worker_profile_and_daily_feedback'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='status',
            field=models.CharField(
                choices=[
                    ('active', 'Active'),
                    ('completed', 'Completed'),
                    ('inactive', 'Inactive'),
                    ('pending', 'Pending (legacy)'),
                ],
                default='active',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='client',
            name='training_interest',
            field=models.CharField(
                choices=[
                    ('capsa', 'CAPSA'),
                    ('citybuild', 'City Build'),
                    ('pit_stop', 'Pit Stop'),
                    ('guard_card', 'Guard Card Program'),
                    ('general', 'General Employment Assistance'),
                ],
                default='general',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='pit_stop_stage',
            field=models.CharField(
                choices=[
                    ('applicant', 'Applicant - Not yet accepted'),
                    ('active_participant', 'Active Participant'),
                    ('worker', 'Worker (has WorkerAccount)'),
                    ('exited', 'Exited Program'),
                    ('waitlisted', 'Waitlisted'),
                ],
                default='applicant',
                help_text='Pit Stop lifecycle stage used to protect applicants, active participants, workers, and exited clients.',
                max_length=30,
            ),
        ),
        migrations.RunPython(mark_existing_worker_accounts, migrations.RunPython.noop),
        migrations.CreateModel(
            name='GuardCardEnrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('can_work_us', models.BooleanField(default=False)),
                ('is_veteran', models.BooleanField(default=False)),
                ('orientation_completed', models.BooleanField(default=False)),
                ('orientation_date', models.DateField(blank=True, null=True)),
                ('training_in_progress', models.BooleanField(default=False)),
                ('guard_card_obtained', models.BooleanField(default=False)),
                ('guard_card_date', models.DateField(blank=True, null=True)),
                (
                    'barrier',
                    models.CharField(
                        choices=[
                            ('transportation', 'Transportation'),
                            ('childcare', 'Childcare'),
                            ('housing_instability', 'Housing instability'),
                            ('missing_id_docs', 'Missing ID/docs'),
                            ('language', 'Language'),
                            ('health_disability', 'Health/disability'),
                            ('criminal_history', 'Criminal history'),
                            ('scheduling_conflict', 'Scheduling conflict'),
                            ('financial_hardship', 'Financial hardship'),
                            ('other', 'Other'),
                            ('none', 'None'),
                        ],
                        default='none',
                        max_length=30,
                    ),
                ),
                ('barrier_notes', models.TextField(blank=True, null=True)),
                (
                    'next_follow_up_date',
                    models.DateField(
                        blank=True,
                        help_text='Auto-set to 30 days from creation when blank.',
                        null=True,
                    ),
                ),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'client',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='guard_card_enrollment',
                        to='clients.client',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Guard Card Enrollment',
                'verbose_name_plural': 'Guard Card Enrollments',
                'ordering': ['next_follow_up_date', 'client__last_name', 'client__first_name'],
            },
        ),
        migrations.AddIndex(
            model_name='guardcardenrollment',
            index=models.Index(fields=['next_follow_up_date'], name='clients_gua_next_fo_d9529a_idx'),
        ),
        migrations.AddIndex(
            model_name='guardcardenrollment',
            index=models.Index(fields=['barrier'], name='clients_gua_barrier_9a90b6_idx'),
        ),
    ]
