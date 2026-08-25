# City Build pipeline stages, and a purpose tag for class change texts.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0050_drop_workassignment_and_partners'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='citybuild_stage',
            field=models.CharField(
                choices=[
                    ('general_interest', 'General interest'),
                    ('interview_scheduled', 'Interview scheduled'),
                    ('interview_completed', 'Interview completed'),
                    ('drug_test', 'Drug test'),
                    ('in_the_running', 'In the running — file submission'),
                    ('waitlisted', 'Waitlisted'),
                    ('accepted', 'Accepted (pre-registration)'),
                    ('dropped', 'Dropped (pre-registration)'),
                    ('enrolled', 'Enrolled (CBA 12-week)'),
                    ('arrived', 'Arrived (CBA 12-week)'),
                    ('completed', 'Completed (CBA 12-week)'),
                ],
                db_index=True,
                default='general_interest',
                help_text=(
                    'City Build pipeline. Accepted/dropped are pre-registration. '
                    'Enrolled/arrived/completed are the CBA 12-week program. '
                    'Drug-test result is not stored.'
                ),
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name='clienttextmessage',
            name='purpose',
            field=models.CharField(
                choices=[
                    ('progress_followup', 'Progress follow-up'),
                    ('class_confirmation', 'Class confirmation'),
                    ('class_update', 'Class update'),
                    ('assignment', 'Assignment'),
                    ('general', 'General'),
                ],
                default='general',
                max_length=30,
            ),
        ),
    ]
