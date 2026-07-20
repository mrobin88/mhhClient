from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copy_legacy_feedback(apps, schema_editor):
    StaffFeedback = apps.get_model('clients', 'StaffFeedback')
    StaffTicket = apps.get_model('clients', 'StaffTicket')
    for fb in StaffFeedback.objects.all().iterator():
        message = (fb.message or '').strip()
        if not message:
            continue
        title = message[:80] + ('…' if len(message) > 80 else '')
        StaffTicket.objects.create(
            title=title[:200],
            description=message,
            status='open',
            priority='p2',
            tags=['other'],
            submitted_by_id=fb.submitted_by_id,
        )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('clients', '0040_remove_guard_card_enrollment'),
    ]

    operations = [
        migrations.CreateModel(
            name='StaffTicket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(help_text='What is needed / what went wrong.')),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('open', 'Open'),
                            ('in_progress', 'In Progress'),
                            ('blocked', 'Blocked'),
                            ('resolved', 'Resolved'),
                            ('closed', 'Closed'),
                        ],
                        default='open',
                        max_length=20,
                    ),
                ),
                (
                    'resolution',
                    models.CharField(
                        blank=True,
                        choices=[
                            ('fixed', 'Fixed / Resolved'),
                            ('wontfix', 'WontFix (Intended Behavior)'),
                            ('working_as_intended', 'WorkingAsIntended'),
                            ('obsolete', 'Obsolete'),
                            ('duplicate', 'Duplicate'),
                            ('cannot_reproduce', 'CannotReproduce'),
                            ('not_reproducible', 'NotReproducible'),
                            ('infeasible', 'Infeasible'),
                        ],
                        default='',
                        max_length=30,
                    ),
                ),
                (
                    'priority',
                    models.CharField(
                        choices=[
                            ('p0', 'P0 — Critical'),
                            ('p1', 'P1 — High'),
                            ('p2', 'P2 — Medium'),
                            ('p3', 'P3 — Low'),
                            ('p4', 'P4 — Nice to have'),
                        ],
                        default='p2',
                        max_length=5,
                    ),
                ),
                (
                    'tags',
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text='List of tag keys, e.g. ["frontend","ui"].',
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                (
                    'assignee',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='assigned_tickets',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'duplicate_of',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='duplicates',
                        to='clients.staffticket',
                    ),
                ),
                (
                    'submitted_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='submitted_tickets',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Staff Ticket',
                'verbose_name_plural': 'Staff Tickets',
                'ordering': ['-updated_at', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='StaffTicketAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='staff_tickets/%Y/%m/')),
                ('original_name', models.CharField(blank=True, max_length=255)),
                ('content_type', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'ticket',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='attachments',
                        to='clients.staffticket',
                    ),
                ),
                (
                    'uploaded_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='ticket_attachments',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Staff Ticket Attachment',
                'verbose_name_plural': 'Staff Ticket Attachments',
                'ordering': ['created_at'],
            },
        ),
        migrations.AlterModelOptions(
            name='stafffeedback',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Staff Feedback (legacy)',
                'verbose_name_plural': 'Staff Feedback (legacy)',
            },
        ),
        migrations.AddIndex(
            model_name='staffticket',
            index=models.Index(fields=['status', 'priority'], name='clients_sta_status_344ef7_idx'),
        ),
        migrations.AddIndex(
            model_name='staffticket',
            index=models.Index(fields=['submitted_by', 'status'], name='clients_sta_submitt_f4217f_idx'),
        ),
        migrations.AddIndex(
            model_name='staffticket',
            index=models.Index(fields=['assignee', 'status'], name='clients_sta_assigne_eeb58f_idx'),
        ),
        migrations.RunPython(copy_legacy_feedback, migrations.RunPython.noop),
    ]
