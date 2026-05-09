from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0021_workertimepunch'),
    ]

    operations = [
        migrations.AddField(
            model_name='workertimepunch',
            name='clock_in_geo_basic_note',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='workertimepunch',
            name='clock_in_geo_basic_ok',
            field=models.BooleanField(default=False, help_text='Basic validation check for clock-in location payload.'),
        ),
        migrations.AddField(
            model_name='workertimepunch',
            name='clock_out_geo_basic_note',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='workertimepunch',
            name='clock_out_geo_basic_ok',
            field=models.BooleanField(default=False, help_text='Basic validation check for clock-out location payload.'),
        ),
        migrations.CreateModel(
            name='WorkerPortalNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('note_type', models.CharField(choices=[('general', 'General update'), ('restroom_check', 'Restroom check update'), ('incident', 'Incident report'), ('supply', 'Supply request')], default='general', max_length=30)),
                ('content', models.TextField()),
                ('staff_response', models.TextField(blank=True)),
                ('is_read_by_staff', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('worker_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='portal_notes', to='clients.workeraccount')),
            ],
            options={
                'verbose_name': 'Worker Portal Note',
                'verbose_name_plural': 'Worker Portal Notes',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='WorkerTimeOffRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('reason', models.TextField()),
                ('status', models.CharField(choices=[('pending', 'Pending review'), ('approved', 'Approved'), ('denied', 'Denied'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('staff_note', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('worker_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='time_off_requests', to='clients.workeraccount')),
            ],
            options={
                'verbose_name': 'Worker Time Off Request',
                'verbose_name_plural': 'Worker Time Off Requests',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='workerportalnote',
            index=models.Index(fields=['worker_account', 'created_at'], name='clients_wor_worker__6d1f35_idx'),
        ),
        migrations.AddIndex(
            model_name='workerportalnote',
            index=models.Index(fields=['is_read_by_staff'], name='clients_wor_is_read__cc0c4b_idx'),
        ),
        migrations.AddIndex(
            model_name='workertimeoffrequest',
            index=models.Index(fields=['worker_account', 'status'], name='clients_wor_worker__4c5404_idx'),
        ),
        migrations.AddIndex(
            model_name='workertimeoffrequest',
            index=models.Index(fields=['start_date', 'end_date'], name='clients_wor_start_d_7c7c07_idx'),
        ),
    ]
