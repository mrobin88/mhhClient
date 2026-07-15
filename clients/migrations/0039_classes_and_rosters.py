from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0038_staff_feedback'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClassTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='e.g. "New Client Orientation" or "Resume Workshop"', max_length=150)),
                (
                    'category',
                    models.CharField(
                        choices=[
                            ('orientation', 'Orientation'),
                            ('job_readiness', 'Job Readiness Training'),
                            ('resume_workshop', 'Resume & Application Workshop'),
                            ('training', 'Skills Training'),
                            ('other', 'Other'),
                        ],
                        default='training',
                        max_length=20,
                    ),
                ),
                ('description', models.TextField(blank=True)),
                ('location', models.CharField(blank=True, help_text='Room or address; can be overridden per session.', max_length=200)),
                ('facilitator', models.CharField(blank=True, help_text='Staff member or presenter running this class.', max_length=100)),
                ('capacity', models.PositiveIntegerField(default=20, help_text='Default seat limit for generated sessions.')),
                ('start_time', models.TimeField(help_text='Default start time for generated sessions.')),
                ('end_time', models.TimeField(help_text='Default end time for generated sessions.')),
                (
                    'recurrence',
                    models.CharField(
                        choices=[
                            ('none', 'Does not repeat'),
                            ('weekly', 'Weekly'),
                            ('monthly', 'Monthly'),
                        ],
                        default='none',
                        max_length=10,
                    ),
                ),
                (
                    'recurrence_weekday',
                    models.PositiveSmallIntegerField(
                        blank=True,
                        choices=[
                            (0, 'Monday'),
                            (1, 'Tuesday'),
                            (2, 'Wednesday'),
                            (3, 'Thursday'),
                            (4, 'Friday'),
                            (5, 'Saturday'),
                            (6, 'Sunday'),
                        ],
                        help_text='Required for weekly/monthly recurrence.',
                        null=True,
                    ),
                ),
                (
                    'recurrence_week_of_month',
                    models.PositiveSmallIntegerField(
                        blank=True,
                        choices=[(1, '1st'), (2, '2nd'), (3, '3rd'), (4, '4th')],
                        help_text='Required for monthly recurrence, e.g. 2nd Tuesday of every month.',
                        null=True,
                    ),
                ),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Class / Training Template',
                'verbose_name_plural': 'Classes & Trainings',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='ClassSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_date', models.DateField()),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('location', models.CharField(blank=True, max_length=200)),
                ('facilitator', models.CharField(blank=True, max_length=100)),
                ('capacity', models.PositiveIntegerField(default=20)),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('scheduled', 'Scheduled'),
                            ('completed', 'Completed'),
                            ('cancelled', 'Cancelled'),
                        ],
                        default='scheduled',
                        max_length=12,
                    ),
                ),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'template',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='sessions',
                        to='clients.classtemplate',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Class Session',
                'verbose_name_plural': 'Class Sessions',
                'ordering': ['session_date', 'start_time'],
            },
        ),
        migrations.CreateModel(
            name='ClassEnrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('registered', 'Registered'),
                            ('attended', 'Attended'),
                            ('no_show', 'No Show'),
                            ('cancelled', 'Cancelled'),
                        ],
                        default='registered',
                        max_length=12,
                    ),
                ),
                ('registered_by', models.CharField(blank=True, help_text='Staff member who added this client.', max_length=100)),
                ('registered_at', models.DateTimeField(auto_now_add=True)),
                ('notes', models.TextField(blank=True)),
                (
                    'client',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='class_enrollments',
                        to='clients.client',
                    ),
                ),
                (
                    'session',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='enrollments',
                        to='clients.classsession',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Class Roster Entry',
                'verbose_name_plural': 'Class Roster',
                'ordering': ['-registered_at'],
            },
        ),
        migrations.AddIndex(
            model_name='classsession',
            index=models.Index(fields=['session_date'], name='classsession_date_idx'),
        ),
        migrations.AddIndex(
            model_name='classsession',
            index=models.Index(fields=['status', 'session_date'], name='classsession_status_date_idx'),
        ),
        migrations.AddConstraint(
            model_name='classenrollment',
            constraint=models.UniqueConstraint(fields=('session', 'client'), name='uniq_class_session_client'),
        ),
    ]
