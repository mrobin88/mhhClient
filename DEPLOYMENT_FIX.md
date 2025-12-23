# 🚀 Deployment Pipeline - Clean Configuration

## ✅ What Was Fixed

### 1. **manage.py Settings Mismatch**
- **Before**: `config.settings` (wrong)
- **After**: `config.simple_settings` (matches wsgi.py)

### 2. **GitHub Actions Workflow**
- **Before**: Deployed from `./backend` folder
- **After**: Deploys from root (`.`)
- **Before**: Only watched `backend/**` paths
- **After**: Watches root Django files (`config/**`, `clients/**`, `users/**`, etc.)

### 3. **.deployment File**
- **Before**: Had `PYTHON_VERSION=3.11` (redundant - runtime.txt handles this)
- **After**: Only `SCM_DO_BUILD_DURING_DEPLOYMENT=true`

### 4. **Project Structure**
- Django project is at **ROOT** (not in `backend/`)
- `backend/` folder exists but is **NOT used for deployment**
- Root has: `manage.py`, `requirements.txt`, `runtime.txt`, `config/`, `clients/`, `users/`

## 📋 Current Deployment Flow

```
Code Push → GitHub Actions → Azure App Service
   ↓
1. GitHub Actions detects changes in root Django files
2. Deploys entire root directory (`.`) to Azure
3. Azure Oryx detects Python from `runtime.txt`
4. Oryx builds: creates venv, installs deps, runs collectstatic
5. Azure runs `startup.sh` → Gunicorn starts Django
```

## 🔧 Key Files

### Root Level (Deployed to Azure)
- `manage.py` - Django management (uses `config.simple_settings`)
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python 3.11
- `startup.sh` - Gunicorn startup script
- `.deployment` - Azure build config
- `config/` - Django settings
- `clients/` - Clients app
- `users/` - Users app

### backend/ Folder
- **NOT used for deployment**
- Contains old/duplicate files
- Can be removed or kept for reference

## ✅ Verification Checklist

After deployment, verify:
1. ✅ `manage.py` uses `config.simple_settings`
2. ✅ `wsgi.py` uses `config.simple_settings`
3. ✅ GitHub Actions deploys from root
4. ✅ `runtime.txt` exists at root
5. ✅ `startup.sh` exists at root
6. ✅ `.deployment` has `SCM_DO_BUILD_DURING_DEPLOYMENT=true`

## 🚨 If Deployment Still Fails

1. Check Azure Portal → Deployment Center → Logs
2. Look for Oryx build output
3. Verify it detects Python (not .NET)
4. Check that `pip install -r requirements.txt` runs
5. Verify Gunicorn starts successfully

