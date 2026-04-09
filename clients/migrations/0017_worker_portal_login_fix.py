import re

from django.db import migrations, models


def normalize_worker_phones_and_sync_flags(apps, schema_editor):
    """Digits-only phones for login; align legacy is_approved with is_active."""
    WorkerAccount = apps.get_model('clients', 'WorkerAccount')
    for wa in WorkerAccount.objects.all().only('id', 'phone', 'is_active', 'is_approved'):
        updates = {}
        raw = wa.phone or ''
        digits = re.sub(r'\D', '', raw)
        if digits and digits != raw:
            updates['phone'] = digits
        if wa.is_active != wa.is_approved:
            updates['is_approved'] = wa.is_active
        if updates:
            WorkerAccount.objects.filter(pk=wa.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0016_update_document_doc_type_choices'),
    ]

    operations = [
        migrations.RunPython(normalize_worker_phones_and_sync_flags, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='workeraccount',
            name='is_active',
            field=models.BooleanField(
                default=True,
                help_text='When on, this worker can log in to the PitStop worker portal.',
                verbose_name='Portal access',
            ),
        ),
        migrations.AlterField(
            model_name='workeraccount',
            name='is_approved',
            field=models.BooleanField(
                default=True,
                help_text='Synced with portal access; kept for compatibility',
            ),
        ),
    ]
