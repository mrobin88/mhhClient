# Azure Blob Storage Path Fix

## Problem

Database contains paths with `client-docs/` prefix (e.g., `client-docs/resumes/file.pdf`), but Azure blob storage has files without that prefix (e.g., `resumes/file.pdf`). This causes "BlobNotFound" errors.

## Root Cause

Migrations `0004` and `0008` incorrectly added `client-docs/` to `upload_to` paths. Django-storages already handles the container name, so this created incorrect database paths.

## Solution

Migration `0010_fix_blob_paths.py` removes the `client-docs/` prefix from database paths.

## Running the Fix on Azure

### Option 1: Kudu Console (Recommended)

1. Go to Azure Portal → Your App Service → Advanced Tools → Go
2. Click "Debug console" → "CMD" or "PowerShell"
3. Navigate to your app directory:
   ```bash
   cd /home/site/wwwroot
   ```

4. Activate virtual environment:
   ```bash
   source antenv/bin/activate
   ```

5. Run migration:
   ```bash
   python manage.py migrate clients 0010
   ```

6. Verify:
   ```bash
   python manage.py showmigrations clients
   ```

### Option 2: SSH (if enabled)

1. Enable SSH for your App Service
2. Connect via Azure Portal SSH or `az webapp ssh`
3. Follow same steps as Kudu console

### Option 3: Auto-deploy

The migration will run automatically on next deployment via `startup.sh`.

## Verification

After running the migration:

1. Go to Django Admin → Documents
2. Select any document
3. Use the "🔍 Check Storage Configuration & Environment" action
4. Verify the document file paths no longer have `client-docs/` prefix
5. Try downloading a document - it should work now

## What the Migration Does

1. **Client resumes**: Removes `client-docs/resumes/` → `resumes/`
2. **Document files**: Removes `client-docs/` → `` and adds `documents/` if needed
3. **Prints progress**: Shows which records were fixed

## Commands Reference

```bash
# Check current migration status
python manage.py showmigrations clients

# Run the fix migration
python manage.py migrate clients 0010

# Check blob storage config (Django shell)
python manage.py shell
>>> from clients.storage import get_azure_container_client
>>> client = get_azure_container_client()
>>> blobs = list(client.list_blobs(max_results=10))
>>> for blob in blobs:
...     print(f"{blob.name} ({blob.size} bytes)")

# List actual database paths
>>> from clients.models import Client, Document
>>> Client.objects.exclude(resume='').values_list('id', 'resume', named=True)[:5]
>>> Document.objects.values_list('id', 'file', named=True)[:5]
```

## Expected Results

**Before fix:**
- Database: `client-docs/resumes/file.pdf`
- Azure: `resumes/file.pdf`
- Result: BlobNotFound error

**After fix:**
- Database: `resumes/file.pdf`
- Azure: `resumes/file.pdf`
- Result: File downloads successfully

## Rollback (if needed)

If something goes wrong:

```bash
# Rollback to previous migration
python manage.py migrate clients 0009

# Or restore from database backup
```

## Notes

- This migration is safe to run multiple times (idempotent)
- It only updates paths that have the `client-docs/` prefix
- No files are moved in Azure - only database paths are updated
- The migration will print which records were fixed
