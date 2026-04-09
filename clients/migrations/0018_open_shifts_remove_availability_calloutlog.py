import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0017_worker_portal_login_fix'),
    ]

    operations = [
        migrations.CreateModel(
            name='OpenShift',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role_title', models.CharField(help_text='Role or type of shift', max_length=200)),
                ('location_label', models.CharField(blank=True, help_text='Use if no work site is selected, or to add extra location detail', max_length=300)),
                ('shift_date', models.DateField()),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('notes', models.TextField(blank=True, help_text='Shown to workers (keep short)')),
                ('created_by', models.CharField(blank=True, help_text='Staff or supervisor name', max_length=200)),
                ('is_open', models.BooleanField(default=True, help_text='Turn off when the shift is filled or cancelled')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'work_site',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='open_shifts',
                        to='clients.worksite',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Open shift (needs coverage)',
                'verbose_name_plural': 'Open shifts (need coverage)',
                'ordering': ['shift_date', 'start_time'],
            },
        ),
        migrations.CreateModel(
            name='ShiftCoverInterest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('pending', 'Interest noted — staff may follow up'),
                            ('selected', 'Selected for this shift'),
                            ('not_selected', 'Not selected (shift filled another way)'),
                            ('cancelled', 'Shift no longer open'),
                        ],
                        default='pending',
                        max_length=20,
                    ),
                ),
                ('staff_note', models.TextField(blank=True, help_text='Internal note (workers do not see this)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'open_shift',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='cover_interests',
                        to='clients.openshift',
                    ),
                ),
                (
                    'worker_account',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='shift_cover_interests',
                        to='clients.workeraccount',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Shift cover interest',
                'verbose_name_plural': 'Shift cover interests',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='shiftcoverinterest',
            constraint=models.UniqueConstraint(
                fields=('worker_account', 'open_shift'),
                name='uniq_worker_openshift_interest',
            ),
        ),
        migrations.DeleteModel(
            name='CallOutLog',
        ),
        migrations.DeleteModel(
            name='ClientAvailability',
        ),
    ]
