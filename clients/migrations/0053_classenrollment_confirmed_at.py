# Clients can reply YES to confirm they are coming to a class.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0052_classtemplate_program'),
    ]

    operations = [
        migrations.AddField(
            model_name='classenrollment',
            name='confirmed_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When the client replied YES to confirm they are coming.',
                null=True,
            ),
        ),
    ]
