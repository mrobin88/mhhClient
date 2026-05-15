from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0023_simplified_pitstop_roster'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientTextMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('direction', models.CharField(choices=[('outbound', 'Outbound'), ('inbound', 'Inbound')], default='outbound', max_length=20)),
                ('purpose', models.CharField(choices=[('progress_followup', 'Progress follow-up'), ('assignment', 'Assignment'), ('general', 'General')], default='general', max_length=30)),
                ('checkpoint_days', models.PositiveIntegerField(blank=True, null=True)),
                ('dedupe_key', models.CharField(blank=True, max_length=120, null=True, unique=True)),
                ('to_phone', models.CharField(blank=True, max_length=20)),
                ('from_phone', models.CharField(blank=True, max_length=20)),
                ('body', models.TextField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed'), ('received', 'Received')], default='pending', max_length=20)),
                ('provider_message_id', models.CharField(blank=True, max_length=120)),
                ('provider_response', models.JSONField(blank=True, default=dict)),
                ('error_message', models.TextField(blank=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('received_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='text_messages', to='clients.client')),
            ],
            options={
                'verbose_name': 'Client Text Message',
                'verbose_name_plural': 'Client Text Messages',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='clienttextmessage',
            index=models.Index(fields=['client', 'purpose', 'checkpoint_days'], name='clients_cli_client__94003a_idx'),
        ),
        migrations.AddIndex(
            model_name='clienttextmessage',
            index=models.Index(fields=['status', 'created_at'], name='clients_cli_status_c15e3a_idx'),
        ),
        migrations.AddIndex(
            model_name='clienttextmessage',
            index=models.Index(fields=['direction', 'created_at'], name='clients_cli_directi_58870c_idx'),
        ),
    ]
