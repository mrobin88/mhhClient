from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0019_alter_client_dob_nullable'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='document',
            name='doc_type',
            field=models.CharField(
                choices=[
                    ('resume', 'Resume'),
                    ('sf_residency', 'Proof of SF Residency'),
                    ('hs_diploma', 'High School Diploma / GED'),
                    ('id', 'Government ID'),
                    ('photo_release', 'Photo Release Form'),
                    ('employment_proof', 'Proof of Employment'),
                    ('self_attestation', 'Employment Self-Attestation'),
                    ('intake', 'Intake Form'),
                    ('consent', 'Consent Form'),
                    ('certificate', 'Certificate/Credential'),
                    ('reference', 'Reference Letter'),
                    ('other', 'Other Document'),
                ],
                default='other',
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='JobPlacement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('employer', models.CharField(max_length=150)),
                ('work_type', models.CharField(choices=[('full_time', 'Full-time'), ('part_time', 'Part-time'), ('contract', 'Contract')], max_length=20)),
                ('job_title', models.CharField(blank=True, max_length=120, null=True)),
                ('hourly_rate', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('start_date', models.DateField()),
                ('employer_address', models.CharField(blank=True, max_length=255, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_by_name', models.CharField(blank=True, default='', max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='job_placements', to='clients.client')),
                ('created_by_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='logged_job_placements', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Job Placement',
                'verbose_name_plural': 'Job Placements',
                'ordering': ['-start_date', '-created_at'],
            },
        ),
    ]
