#!/bin/bash
# Build script for Azure Oryx
# This ensures dependencies are installed during the build phase

echo "=== Oryx Build Phase ==="
echo "Working directory: $(pwd)"

# If we're in the root, check for requirements.txt
if [ -f "requirements.txt" ]; then
    echo "Found requirements.txt in root"
    pip install --upgrade pip
    pip install -r requirements.txt
elif [ -f "backend/requirements.txt" ]; then
    echo "Found requirements.txt in backend/"
    pip install --upgrade pip
    pip install -r backend/requirements.txt
else
    echo "WARNING: requirements.txt not found"
fi

echo "Build phase complete"

