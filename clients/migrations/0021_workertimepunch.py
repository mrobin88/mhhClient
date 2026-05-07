from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0020_jobplacement_and_employment_doc_types'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkerTimePunch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('clock_in_at', models.DateTimeField()),
                ('clock_out_at', models.DateTimeField(blank=True, null=True)),
                ('clock_in_server_received_at', models.DateTimeField(auto_now_add=True)),
                ('clock_out_server_received_at', models.DateTimeField(blank=True, null=True)),
                ('clock_in_client_reported_at', models.DateTimeField(blank=True, null=True)),
                ('clock_out_client_reported_at', models.DateTimeField(blank=True, null=True)),
                ('clock_in_latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('clock_in_longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('clock_in_accuracy_meters', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('clock_in_geo_status', models.CharField(choices=[('captured', 'Location captured'), ('denied', 'Location permission denied'), ('unavailable', 'Location unavailable'), ('timeout', 'Location lookup timed out'), ('error', 'Location lookup failed'), ('skipped', 'Location not attempted')], default='skipped', max_length=20)),
                ('clock_in_geo_error', models.CharField(blank=True, max_length=200)),
                ('clock_out_latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('clock_out_longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('clock_out_accuracy_meters', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('clock_out_geo_status', models.CharField(choices=[('captured', 'Location captured'), ('denied', 'Location permission denied'), ('unavailable', 'Location unavailable'), ('timeout', 'Location lookup timed out'), ('error', 'Location lookup failed'), ('skipped', 'Location not attempted')], default='skipped', max_length=20)),
                ('clock_out_geo_error', models.CharField(blank=True, max_length=200)),
                ('worker_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='time_punches', to='clients.workeraccount')),
            ],
            options={
                'verbose_name': 'Worker Time Punch',
                'verbose_name_plural': 'Worker Time Punches',
                'ordering': ['-clock_in_at'],
            },
        ),
        migrations.AddIndex(
            model_name='workertimepunch',
            index=models.Index(fields=['worker_account', 'clock_out_at'], name='clients_wor_worker__0a4f3e_idx'),
        ),
        migrations.AddIndex(
            model_name='workertimepunch',
            index=models.Index(fields=['clock_in_at'], name='clients_wor_clock_i_1f10d7_idx'),
        ),
    ]
