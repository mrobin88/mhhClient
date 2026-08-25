# Drop leftover WorkAssignment scheduling and the unused partner mail-slot.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0049_rename_clients_cli_client__94003a_idx_clients_cli_client__8136b7_idx_and_more'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='workertimepunch',
            name='clients_wor_assignm_cb0f7b_idx',
        ),
        migrations.RemoveField(
            model_name='workertimepunch',
            name='assignment',
        ),
        migrations.DeleteModel(
            name='WorkAssignment',
        ),
        migrations.DeleteModel(
            name='PartnerReferral',
        ),
        migrations.DeleteModel(
            name='PartnerApiAuditLog',
        ),
        migrations.DeleteModel(
            name='Partner',
        ),
    ]
