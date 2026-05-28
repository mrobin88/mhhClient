from datetime import date

from django.db import migrations, models


def backfill_note_date(apps, schema_editor):
    CaseNote = apps.get_model('clients', 'CaseNote')
    for note in CaseNote.objects.filter(note_date__isnull=True).iterator():
        if note.created_at:
            note.note_date = note.created_at.date()
        else:
            note.note_date = date.today()
        note.save(update_fields=['note_date'])


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0028_worker_time_punch_lunch'),
    ]

    operations = [
        migrations.AddField(
            model_name='casenote',
            name='note_date',
            field=models.DateField(
                help_text='Date the interaction happened (use for retroactive entry).',
                null=True,
            ),
        ),
        migrations.RunPython(backfill_note_date, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='casenote',
            name='note_date',
            field=models.DateField(
                default=date.today,
                help_text='Date the interaction happened (use for retroactive entry).',
            ),
        ),
    ]
