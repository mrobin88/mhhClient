# Azure Blob Storage Path Fix – Kudu Console Python Troubleshooting

## Problem

Some database file paths incorrectly include the `client-docs/` prefix (e.g., `client-docs/resumes/file.pdf`), but Azure Blob Storage files do **not** have this prefix (they are just `resumes/file.pdf`). This causes "BlobNotFound" errors when trying to access files.

## Root Cause

Older migrations (`0004` and `0008`) mistakenly included the `client-docs/` container name in `upload_to` paths. However, Django-storages already handles the container, so database paths became incorrect.

## Solution

Migration `0010_fix_blob_paths.py` strips the `client-docs/` prefix from database paths.

---

## Running the Migration (with Python Issues in Kudu/SSH)

On Azure App Service (Linux), Python may not be accessible as `python`. Here are the steps:

1. **Open Kudu Console** (Azure Portal → Your App Service → Advanced Tools → Go).
2. Click "Debug console" → "CMD" or "PowerShell".
3. Navigate to your app code:
    ```bash
    cd /home/site/wwwroot
    ```
4. **Activate the virtual environment** (if not already):
    ```bash
    source antenv/bin/activate
    ```
5. **Check which Python executable works:**
    ```bash
    python --version         # (may not be found)
    python3 --version        # (should work)
    ```
    If `python` fails with "command not found", **use `python3`** for all commands:

6. **Apply the migration:**
    ```bash
    python3 manage.py migrate clients 0010
    ```
    If you see `ModuleNotFoundError: No module named 'django'`, make sure your virtual environment is actually activated and contains Django.

7. **If still failing, check the following:**

    - Virtual environment path might be different: try `source .venv/bin/activate` or `source env/bin/activate` if `antenv` is missing.
    - Check `requirements.txt` and (re)install dependencies:
      ```bash
      pip install -r requirements.txt
      ```

8. **Verify:**
    ```bash
    python3 manage.py showmigrations clients
    ```

---

## SSH Troubleshooting Example

If using SSH (via Azure Portal or `az webapp ssh`), follow the same steps as above.

- Always use `python3` if `python` is not available.
- Example session:
    ```
    kudu_ssh_user@aa175e27f340:~/site/wwwroot$ source antenv/bin/activate
    (antenv) kudu_ssh_user@aa175e27f340:~/site/wwwroot$ python manage.py migrate clients 0010
    -bash: python: command not found
    (antenv) kudu_ssh_user@aa175e27f340:~/site/wwwroot$ python3 manage.py migrate clients 0010
    ```

---

## Verification Steps

After the migration runs:

1. Go to Django Admin → Documents
2. Select a document
3. Use the "🔍 Check Storage Configuration & Environment" action
4. The file path shown should **not** include `client-docs/`
5. File downloads should now work

---

## What the Migration Does

- **Client resumes:** Changes `client-docs/resumes/` → `resumes/`
- **Document files:** Removes `client-docs/` and adds `documents/` if needed for document files
- Prints a progress log showing which records it fixed

---

## Commands Reference

```bash
# Show migration status
python3 manage.py showmigrations clients

# Run the path fix migration
python3 manage.py migrate clients 0010

# Inspect some Azure blobs
python3 manage.py shell
>>> from clients.storage import get_azure_container_client
>>> client = get_azure_container_client()
>>> blobs = list(client.list_blobs(max_results=10))
>>> for blob in blobs:
...     print(f"{blob.name} ({blob.size} bytes)")

# See actual database paths
>>> from clients.models import Client, Document
>>> Client.objects.exclude(resume='').values_list('id', 'resume', named=True)[:5]
>>> Document.objects.values_list('id', 'file', named=True)[:5]
```

---

## Expected Results

**Before migration:**
- Database: `client-docs/resumes/file.pdf`
- Azure: `resumes/file.pdf`
- Result: BlobNotFound error

**After migration:**
- Database: `resumes/file.pdf`
- Azure: `resumes/file.pdf`
- Result: File downloads successfully

---

## Rollback

If you need to undo this migration:

```bash
python3 manage.py migrate clients 0009
# Or restore from DB backup if you have one
```

---

## Notes

- The migration is safe to run multiple times (idempotent)
- Only updates paths **with** `client-docs/` prefix
- Does **not** move or rename blobs in Azure—DB update only!
- Progress will be printed in the logs/console

