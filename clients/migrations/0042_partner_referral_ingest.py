# Partner write-only referral ingest

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0041_staff_tickets'),
    ]

    operations = [
        migrations.CreateModel(
            name='Partner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=80, unique=True)),
                ('contact_name', models.CharField(blank=True, max_length=120)),
                ('contact_email', models.EmailField(blank=True, max_length=254)),
                ('is_active', models.BooleanField(default=True, help_text='Off = all API calls with this partner’s key are rejected.')),
                ('notes', models.TextField(blank=True, help_text='Internal notes (contracts, billing).')),
                ('api_key_prefix', models.CharField(blank=True, editable=False, max_length=16)),
                ('api_key_hash', models.CharField(blank=True, db_index=True, editable=False, max_length=64)),
                ('api_key_created_at', models.DateTimeField(blank=True, editable=False, null=True)),
                ('request_count', models.PositiveIntegerField(default=0, help_text='Successful ingest calls (for invoice support).')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Partner',
                'verbose_name_plural': 'Partners',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='PartnerApiAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('method', models.CharField(max_length=10)),
                ('path', models.CharField(max_length=200)),
                ('status_code', models.PositiveSmallIntegerField()),
                ('external_id', models.CharField(blank=True, max_length=120)),
                ('detail', models.CharField(blank=True, max_length=200)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('partner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to='clients.partner')),
            ],
            options={
                'verbose_name': 'Partner API audit log',
                'verbose_name_plural': 'Partner API audit logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PartnerReferral',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_id', models.CharField(help_text='Partner’s stable id (e.g. Airtable record id).', max_length=120)),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('phone', models.CharField(blank=True, max_length=40)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('notes', models.TextField(blank=True, max_length=2000)),
                ('status', models.CharField(choices=[('pending', 'Pending review'), ('reviewed', 'Reviewed'), ('accepted', 'Accepted'), ('declined', 'Declined')], default='pending', max_length=20)),
                ('staff_notes', models.TextField(blank=True, help_text='Internal follow-up notes.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('linked_client', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='partner_referrals', to='clients.client')),
                ('partner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='referrals', to='clients.partner')),
            ],
            options={
                'verbose_name': 'Partner referral',
                'verbose_name_plural': 'Partner referrals',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='partnerreferral',
            index=models.Index(fields=['partner', 'status'], name='clients_par_partner_737771_idx'),
        ),
        migrations.AddIndex(
            model_name='partnerreferral',
            index=models.Index(fields=['-created_at'], name='clients_par_created_c0aa1d_idx'),
        ),
        migrations.AddConstraint(
            model_name='partnerreferral',
            constraint=models.UniqueConstraint(fields=('partner', 'external_id'), name='uniq_partner_referral_external_id'),
        ),
        migrations.AddIndex(
            model_name='partnerapiauditlog',
            index=models.Index(fields=['partner', '-created_at'], name='clients_par_partner_2aed58_idx'),
        ),
    ]
