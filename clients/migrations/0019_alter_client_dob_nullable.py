from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0018_open_shifts_remove_availability_calloutlog'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='dob',
            field=models.DateField(blank=True, null=True),
        ),
    ]
