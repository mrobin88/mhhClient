from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0024_client_text_message'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkerShiftProof',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('photo', models.ImageField(help_text='Photo submitted by the worker from the post.', upload_to='worker_shift_proofs/')),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('client_reported_at', models.DateTimeField(blank=True, null=True)),
                ('latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('accuracy_meters', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('geo_status', models.CharField(choices=[('captured', 'Location captured'), ('denied', 'Location permission denied'), ('unavailable', 'Location unavailable'), ('timeout', 'Location lookup timed out'), ('error', 'Location lookup failed'), ('skipped', 'Location not attempted')], default='skipped', max_length=20)),
                ('geo_error', models.CharField(blank=True, max_length=200)),
                ('geo_basic_ok', models.BooleanField(default=False, help_text='Basic validation check for submitted browser location.')),
                ('geo_basic_note', models.CharField(blank=True, max_length=200)),
                ('staff_note', models.TextField(blank=True)),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shift_proofs', to='clients.workassignment')),
                ('worker_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shift_proofs', to='clients.workeraccount')),
            ],
            options={
                'verbose_name': 'Worker Shift Proof',
                'verbose_name_plural': 'Worker Shift Proofs',
                'ordering': ['-submitted_at'],
            },
        ),
        migrations.AddIndex(
            model_name='workershiftproof',
            index=models.Index(fields=['worker_account', 'submitted_at'], name='clients_wor_worker__0a367a_idx'),
        ),
        migrations.AddIndex(
            model_name='workershiftproof',
            index=models.Index(fields=['assignment', 'submitted_at'], name='clients_wor_assignm_0831db_idx'),
        ),
        migrations.AddIndex(
            model_name='workershiftproof',
            index=models.Index(fields=['geo_status', 'submitted_at'], name='clients_wor_geo_sta_725535_idx'),
        ),
    ]
