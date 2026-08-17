# Allow ClientTextMessage rows to be tagged as class signup confirmations.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0043_add_guard_card_program'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clienttextmessage',
            name='purpose',
            field=models.CharField(
                choices=[
                    ('progress_followup', 'Progress follow-up'),
                    ('class_confirmation', 'Class confirmation'),
                    ('assignment', 'Assignment'),
                    ('general', 'General'),
                ],
                default='general',
                max_length=30,
            ),
        ),
    ]
