# Digital Pit Stop application now matches the paper FY 26-27 form
# plus the workforce-program screening questions.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0053_classenrollment_confirmed_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pitstopapplication',
            name='employment_history',
            field=models.JSONField(
                default=list,
                help_text=(
                    'Up to two jobs: company_name, dates_of_employment, city, state, '
                    'manager_name, manager_phone, job_title, responsibilities.'
                ),
            ),
        ),
        migrations.AddField(
            model_name='pitstopapplication',
            name='high_school_name',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='pitstopapplication',
            name='high_school_city',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='pitstopapplication',
            name='high_school_state',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AddField(
            model_name='pitstopapplication',
            name='post_secondary_name',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='pitstopapplication',
            name='post_secondary_city',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='pitstopapplication',
            name='post_secondary_state',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AddField(
            model_name='pitstopapplication',
            name='what_is_pit_stop',
            field=models.TextField(
                blank=True,
                default='',
                help_text='In your own words, what is the Pit Stop program?',
            ),
        ),
        migrations.AddField(
            model_name='pitstopapplication',
            name='why_participate',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Why do you want to participate in Pit Stop?',
            ),
        ),
        migrations.AddField(
            model_name='pitstopapplication',
            name='goals_after_program',
            field=models.TextField(
                blank=True,
                default='',
                help_text='What goals do you have after completing the Pit Stop workforce program?',
            ),
        ),
        migrations.AddField(
            model_name='pitstopapplication',
            name='how_program_supports_goals',
            field=models.TextField(
                blank=True,
                default='',
                help_text='How can this program support your long-term professional goals in joining the workforce?',
            ),
        ),
        migrations.AddField(
            model_name='pitstopapplication',
            name='signature_name',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='pitstopapplication',
            name='signed_on',
            field=models.DateField(blank=True, null=True),
        ),
    ]
