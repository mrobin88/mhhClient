#!/bin/bash
# SECURITY FIX: Remove sensitive files from git tracking
# This script removes sensitive files that should never be in version control

echo "🚨 SECURITY FIX: Removing sensitive files from git tracking..."

# Remove venv directory from git tracking
echo "Removing venv/ directory from git tracking..."
git rm -r --cached venv/ 2>/dev/null || echo "venv/ not tracked or already removed"

# Remove environment files from git tracking
echo "Removing backend/env.local from git tracking..."
git rm --cached backend/env.local 2>/dev/null || echo "backend/env.local not tracked or already removed"

# Remove database files from git tracking
echo "Removing backend/db.sqlite3 from git tracking..."
git rm --cached backend/db.sqlite3 2>/dev/null || echo "backend/db.sqlite3 not tracked or already removed"

# Remove any other .env files that might be tracked
echo "Removing any other .env files from git tracking..."
git rm --cached .env 2>/dev/null || echo ".env not tracked or already removed"
git rm --cached backend/.env 2>/dev/null || echo "backend/.env not tracked or already removed"
git rm --cached frontend/.env 2>/dev/null || echo "frontend/.env not tracked or already removed"

# Remove any other sensitive files
echo "Removing any other sensitive files..."
git rm --cached *.log 2>/dev/null || echo "No log files tracked"
git rm --cached backend/*.log 2>/dev/null || echo "No backend log files tracked"

echo "✅ Sensitive files removed from git tracking!"
echo "📝 Commit these changes to remove them from the repository:"
echo "   git add -A"
echo "   git commit -m 'SECURITY: Remove sensitive files from git tracking'"
echo "   git push origin main"
echo ""
echo "⚠️  IMPORTANT: These files are now only in your local filesystem."
echo "   Make sure to recreate them locally if needed, but NEVER commit them again!"