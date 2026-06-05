from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0030_punch_location_snapshots'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='citybuild_files_confirmed',
            field=models.BooleanField(
                default=False,
                help_text='Staff confirmed CityBuild file packet reviewed (optional).',
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='citybuild_files_confirmed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='citybuild_files_confirmed_by',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='client',
            name='training_interest',
            field=models.CharField(
                choices=[
                    ('citybuild', 'CityBuild Academy'),
                    ('citybuild_pro', 'CityBuild Pro | CAPSA'),
                    ('security', 'Security Guard Card Program'),
                    ('construction', 'Construction On Ramp'),
                    ('pit_stop', 'Pit Stop Program'),
                    ('general', 'General Employment Assistance'),
                    ('other', 'Other training'),
                ],
                default='general',
                max_length=20,
            ),
        ),
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
                    ('employment_proof', 'Proof of Employment'),
                    ('self_attestation', 'Employment Self-Attestation'),
                    ('intake', 'Intake Form'),
                    ('consent', 'Consent Form'),
                    ('certificate', 'Certificate/Credential'),
                    ('reference', 'Reference Letter'),
                    ('cb_application', 'CityBuild Application'),
                    ('cb_roi', 'Release of Information'),
                    ('cb_tabe', 'TABE (top page)'),
                    ('cb_parq', 'Par-Q / Doc Clearance'),
                    ('cb_iep', 'IEP'),
                    ('cb_ssn_card', 'Social Security Card'),
                    ('cb_drug_test', 'Drug Test'),
                    ('cb_safety', 'Safety Form'),
                    ('cb_covid_vax', 'COVID Vaccination'),
                    ('cb_po', 'PO'),
                    ('cb_besi', 'BESI'),
                    ('cb_jrt_eval', 'JRT Eval'),
                    ('cb_rights', 'Rights & Responsibilities'),
                    ('cb_lou', 'Letter of Understanding & Agreement'),
                    ('cb_interview', 'Interview Sheet'),
                    ('cb_emp_edu_verify', 'Employment & Education Verification'),
                    ('cb_support_svc', 'Supportive Service Determination'),
                    ('other', 'Other Document'),
                ],
                default='other',
                max_length=20,
            ),
        ),
    ]
