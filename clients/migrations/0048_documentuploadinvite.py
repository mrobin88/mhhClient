import clients.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('clients', '0047_encrypt_client_ssn'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentUploadInvite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token_hash', models.CharField(max_length=64, unique=True)),
                ('token_prefix', models.CharField(db_index=True, max_length=12)),
                ('allowed_doc_types', models.JSONField(default=list)),
                ('expires_at', models.DateTimeField(db_index=True, default=clients.models.default_upload_invite_expiry)),
                ('max_uploads', models.PositiveSmallIntegerField(default=20)),
                ('upload_count', models.PositiveSmallIntegerField(default=0)),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('last_used_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='document_upload_invites', to='clients.client')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='document_upload_invites_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['client', 'expires_at'], name='docinvite_client_exp_idx')],
            },
        ),
    ]
