from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_staffuser_accent_color'),
    ]

    operations = [
        migrations.AddField(
            model_name='staffuser',
            name='dashboard_collapsed',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Dashboard card ids this staff member has minimized.',
            ),
        ),
    ]
