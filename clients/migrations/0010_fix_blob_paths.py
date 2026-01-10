# Generated manually to fix blob storage paths

from django.db import migrations


def fix_client_resume_paths(apps, schema_editor):
    """Remove 'client-docs/' prefix from Client resume paths"""
    Client = apps.get_model('clients', 'Client')
    
    fixed_count = 0
    for client in Client.objects.exclude(resume=''):
        if client.resume and client.resume.name:
            old_path = client.resume.name
            
            # Remove 'client-docs/' prefix if present
            if old_path.startswith('client-docs/resumes/'):
                new_path = old_path.replace('client-docs/resumes/', 'resumes/', 1)
                client.resume.name = new_path
                client.save(update_fields=['resume'])
                fixed_count += 1
                print(f"Fixed Client {client.id}: {old_path} -> {new_path}")
            elif old_path.startswith('client-docs/'):
                new_path = old_path.replace('client-docs/', '', 1)
                client.resume.name = new_path
                client.save(update_fields=['resume'])
                fixed_count += 1
                print(f"Fixed Client {client.id}: {old_path} -> {new_path}")
    
    print(f"Fixed {fixed_count} client resume paths")


def fix_document_file_paths(apps, schema_editor):
    """Remove 'client-docs/' prefix from Document file paths"""
    Document = apps.get_model('clients', 'Document')
    
    fixed_count = 0
    for doc in Document.objects.all():
        if doc.file and doc.file.name:
            old_path = doc.file.name
            
            # Remove 'client-docs/' prefix if present
            if old_path.startswith('client-docs/'):
                new_path = old_path.replace('client-docs/', '', 1)
                # Also ensure documents/ prefix exists
                if not new_path.startswith('documents/') and not new_path.startswith('resumes/'):
                    new_path = f'documents/{new_path}'
                doc.file.name = new_path
                doc.save(update_fields=['file'])
                fixed_count += 1
                print(f"Fixed Document {doc.id}: {old_path} -> {new_path}")
    
    print(f"Fixed {fixed_count} document file paths")


def reverse_fix(apps, schema_editor):
    """Reverse migration - add back 'client-docs/' prefix"""
    pass  # Not reversing to avoid breaking things further


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0009_alter_pitstopapplication_employment_desired'),
    ]

    operations = [
        migrations.RunPython(fix_client_resume_paths, reverse_fix),
        migrations.RunPython(fix_document_file_paths, reverse_fix),
    ]
