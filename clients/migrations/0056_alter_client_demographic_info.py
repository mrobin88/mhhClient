from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0055_applicantstalealert'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='demographic_info',
            field=models.CharField(choices=[('american_indian', 'American Indian or Alaska Native'), ('asian', 'Asian'), ('black', 'Black or African American'), ('white', 'Caucasian or White'), ('hispanic_latinx', 'Hispanic or Latinx'), ('middle_eastern', 'Middle Eastern'), ('pacific_islander', 'Native Hawaiian or Other Pacific Islander'), ('other', 'Other'), ('decline_state', 'Decline to State'), ('multiracial', 'Multiracial')], default='other', max_length=20),
        ),
    ]
