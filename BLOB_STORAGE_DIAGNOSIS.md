# Blob Storage Resume Access Fix

## Issues Identified

### 1. **API Missing Resume Download URLs**
**Problem:** The `ClientSerializer` was exposing the raw `resume` FileField but NOT the secure `resume_download_url` property. This meant:
- API consumers received blob names like `resumes/file.pdf`
- Direct blob URLs without SAS tokens fail (container is private for security)
- Frontend couldn't generate proper authenticated download links

**Fix Applied:** Updated `ClientSerializer` to include:
- `resume_download_url` - Returns SAS-authenticated URL with 15-minute expiry
- `resume_file_type` - Returns file type (pdf/image/word/other) for preview

### 2. **No Dedicated Resume Download Endpoint**
**Problem:** Documents had `/api/documents/<id>/download/` endpoint, but resumes had no equivalent endpoint.

**Fix Applied:** Added `/api/clients/<id>/resume/` endpoint that:
- Requires authentication
- Generates SAS URL with proper error handling
- Redirects to Azure Blob Storage for direct download
- Handles missing files gracefully

### 3. **Blob Path Issues (Already Fixed by Migration 0010)**
**Status:** Migration `0010_fix_blob_paths.py` already fixed legacy path issues where blob names incorrectly included `client-docs/` prefix.

## How It Works Now

### Admin Interface (Django Admin)
✅ **Working** - Uses `Client.resume_download_url` property which:
1. Calls `generate_resume_sas_url()`
2. Tries `self.resume.url` first (may be SAS URL from storage backend)
3. Falls back to `generate_document_sas_url()` which:
   - Tries multiple path variations (handles legacy paths)
   - Verifies blob exists in Azure before generating SAS
   - Generates SAS token with 15-minute expiry
   - Returns full authenticated URL

### API (REST Endpoints)
✅ **Fixed** - Now includes `resume_download_url` in serialized client data:
```json
{
  "id": 1,
  "full_name": "John Doe",
  "has_resume": true,
  "resume_download_url": "https://account.blob.core.windows.net/client-docs/resumes/file.pdf?se=2026-02-03T20:30:00Z&sp=r&sig=...",
  "resume_file_type": "pdf"
}
```

### Direct Download Endpoint
✅ **Added** - New endpoint: `GET /api/clients/{id}/resume/`
- Requires authentication (login_required)
- Generates fresh SAS URL on each request
- Returns 404 if resume doesn't exist
- Returns 500 with error message if SAS generation fails

## Diagnostic Commands

### 1. Check Azure Storage Configuration
```bash
# Via Django admin - go to Documents, select any document, then:
# Actions → "🔍 Check Storage Configuration & Environment"
```

This admin action shows:
- Environment variables (AZURE_ACCOUNT_NAME, AZURE_ACCOUNT_KEY, AZURE_CONTAINER)
- Container existence and connectivity
- First 10 blobs in container
- Storage backend being used

### 2. Verify Blob Paths in Database
```bash
# SSH into Azure App Service or run locally
python manage.py shell

from clients.models import Client

# Check resume paths
for client in Client.objects.exclude(resume='')[:5]:
    print(f"Client {client.pk}: {client.resume.name}")
    # Should output: resumes/filename.pdf (NOT client-docs/resumes/...)

# Test SAS URL generation
client = Client.objects.exclude(resume='').first()
if client:
    url = client.resume_download_url
    print(f"SAS URL: {url[:100]}...")
```

### 3. Verify Blobs Exist in Azure
```bash
python manage.py shell

from clients.storage import get_azure_container_client

container_client = get_azure_container_client()
if container_client:
    # List all blobs
    blobs = list(container_client.list_blobs())
    print(f"Total blobs: {len(blobs)}")
    
    # Show first 10
    for blob in blobs[:10]:
        print(f"  {blob.name} ({blob.size} bytes)")
    
    # Check specific resume
    from clients.models import Client
    client = Client.objects.exclude(resume='').first()
    if client:
        blob_name = client.resume.name
        blob_client = container_client.get_blob_client(blob_name)
        exists = blob_client.exists()
        print(f"\nClient {client.pk} resume exists: {exists}")
        print(f"Blob path: {blob_name}")
```

### 4. Test API Response
```bash
# Get API response for a client with resume
curl -H "Authorization: Basic <credentials>" \
  https://your-backend.azurewebsites.net/api/clients/1/

# Should include:
# "resume_download_url": "https://account.blob.core.windows.net/client-docs/resumes/file.pdf?..."
# "resume_file_type": "pdf"
```

### 5. Test Direct Download Endpoint
```bash
# Try downloading a resume via the new endpoint
curl -L -H "Authorization: Basic <credentials>" \
  https://your-backend.azurewebsites.net/api/clients/1/resume/ \
  -o downloaded_resume.pdf

# -L follows redirects to Azure Blob Storage
```

## Common Issues & Solutions

### Issue: "BlobNotFound" Error
**Possible Causes:**
1. Database path has wrong prefix (should be `resumes/file.pdf`, not `client-docs/resumes/file.pdf`)
2. Blob was never uploaded to Azure (file only exists locally)
3. Blob was deleted from Azure but database still references it

**Solution:**
```bash
# Run migration 0010 if not already applied
python manage.py migrate clients 0010

# Verify blob exists in Azure (see diagnostic #3 above)

# If blob is missing, re-upload the file via Django admin
```

### Issue: "403 Forbidden" or "401 Unauthorized" When Accessing Resume
**Possible Causes:**
1. SAS token expired (15-minute expiry)
2. SAS token not generated (using direct blob URL instead)
3. Azure credentials not configured (missing AZURE_ACCOUNT_KEY)

**Solution:**
```bash
# Check environment variables are set
echo $AZURE_ACCOUNT_NAME
echo $AZURE_ACCOUNT_KEY
echo $AZURE_CONTAINER

# Verify SAS URL includes query parameters
# Good: https://...blob.core.windows.net/client-docs/resumes/file.pdf?se=2026&sp=r&sig=...
# Bad:  https://...blob.core.windows.net/client-docs/resumes/file.pdf (no SAS token)

# Check storage backend in settings
python manage.py shell
from django.conf import settings
print(settings.DEFAULT_FILE_STORAGE)
# Should be: clients.storage.AzurePrivateStorage
```

### Issue: Resume Shows in Admin But Not in API
**Solution:** This is now fixed! The serializer includes `resume_download_url`.

If still not working:
1. Restart the backend server to pick up code changes
2. Clear any API caches
3. Check the API response includes the new fields

## Files Modified

1. **`clients/serializers.py`** - Added `resume_download_url` and `resume_file_type` to `ClientSerializer`
2. **`clients/views.py`** - Added `ResumeDownloadView` class for direct resume downloads
3. **`clients/urls.py`** - Added `/api/clients/<id>/resume/` endpoint

## Testing Checklist

- [ ] Check Azure Storage configuration via admin action
- [ ] Verify database paths don't have `client-docs/` prefix
- [ ] Verify blobs exist in Azure container
- [ ] Test API returns `resume_download_url` for clients with resumes
- [ ] Test clicking resume link in admin interface
- [ ] Test new `/api/clients/{id}/resume/` endpoint
- [ ] Verify SAS URLs expire after 15 minutes (security check)
- [ ] Test with missing resume (should return null/404 gracefully)

## Security Notes

✅ **Correct Configuration:**
- Azure Blob container is **private** (no public access)
- All downloads require authentication (login_required)
- SAS tokens expire after 15 minutes
- SAS tokens have read-only permissions
- Clock skew handled (SAS start time 5 minutes in past)

❌ **Don't Do This:**
- Don't make the blob container public
- Don't expose raw blob names without SAS tokens
- Don't remove authentication from download endpoints
- Don't extend SAS expiry beyond 1 hour (unnecessary security risk)
