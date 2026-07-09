from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('clients', '0037_guard_card_pipeline_and_pitstop_stage'),
    ]

    operations = [
        migrations.CreateModel(
            name='StaffFeedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField(help_text='Free-text feedback from staff.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('submitted_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='dashboard_feedback',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Staff Feedback',
                'verbose_name_plural': 'Staff Feedback',
                'ordering': ['-created_at'],
            },
        ),
    ]
