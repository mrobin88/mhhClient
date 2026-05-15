from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0014_add_program_start_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='document',
            name='doc_type',
            field=models.CharField(
                choices=[
                    ('resume', 'Resume'),
                    ('sf_residency', 'Proof of SF Residency'),
                    ('hs_diploma', 'High School Diploma / GED'),
                    ('id', 'Government ID'),
                    ('photo_release', 'Photo Release Form'),
                    ('intake', 'Intake Form'),
                    ('consent', 'Consent Form'),
                    ('certificate', 'Certificate/Credential'),
                    ('reference', 'Reference Letter'),
                    ('other', 'Other Document'),
                ],
                default='other',
                max_length=20,
            ),
        ),
    ]
