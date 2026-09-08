from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_staffuser_dashboard_collapsed'),
    ]

    operations = [
        migrations.AddField(
            model_name='staffuser',
            name='dashboard_order',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Dashboard card ids in the order this staff member prefers.',
            ),
        ),
    ]
