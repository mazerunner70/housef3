#!/bin/bash

set -e          # Exit on any error
set -u          # Exit on undefined variables  
set -o pipefail # Exit on pipe failures

echo "=== ML Dependencies Lambda Layer Build Script ==="
echo "Building Lambda Layer for numpy, pandas, scikit-learn, scipy, holidays"

# Cleanup previous build
rm -rf layer_build
rm -f ml_layer.zip

# Create layer directory structure
# Lambda expects packages in python/lib/python3.12/site-packages/
mkdir -p layer_build/python

echo "Installing ML dependencies from requirements-ml.txt..."
pip install \
  -r requirements-ml.txt \
  -t layer_build/python/ \
  --platform manylinux2014_x86_64 \
  --python-version 3.12 \
  --only-binary=:all:

if [ $? -ne 0 ]; then
  echo "❌ CRITICAL ERROR: Failed to install ML dependencies"
  exit 1
fi

echo "Cleaning up unnecessary files..."
cd layer_build/python
# Remove unnecessary files to reduce size
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
# Remove docs, markdown, and test files
find . -type f -name "*.md" -delete 2>/dev/null || true
find . -type f -name "*.rst" -delete 2>/dev/null || true
find . -type f -name "*.txt" -delete 2>/dev/null || true
# Remove test directories more carefully - only those not needed at runtime
find . -path "*/tests/*" -type f -name "test_*.py" -delete 2>/dev/null || true
find . -path "*/testing/*" -delete 2>/dev/null || true
# Remove large unnecessary components
rm -rf */bin/* 2>/dev/null || true
rm -rf */test/* 2>/dev/null || true
rm -rf */tests/data/* 2>/dev/null || true

cd ../..

echo "Creating layer package..."
cd layer_build
zip -r ../ml_layer.zip python/
cd ..

if [ ! -f "ml_layer.zip" ]; then
  echo "❌ CRITICAL ERROR: ml_layer.zip was not created"
  exit 1
fi

LAYER_SIZE=$(stat -c%s "ml_layer.zip")
LAYER_SIZE_MB=$((LAYER_SIZE / 1024 / 1024))
echo "✅ ML Layer created successfully (${LAYER_SIZE_MB}MB)"

if [ "$LAYER_SIZE" -gt 52428800 ]; then  # 50MB
  echo "⚠️  WARNING: Layer size is ${LAYER_SIZE_MB}MB - may need optimization"
fi

# Check unzipped size
cd layer_build
UNZIPPED_SIZE=$(du -sb python | cut -f1)
UNZIPPED_SIZE_MB=$((UNZIPPED_SIZE / 1024 / 1024))
cd ..
echo "Unzipped size: ${UNZIPPED_SIZE_MB}MB"

if [ "$UNZIPPED_SIZE" -gt 262144000 ]; then  # 250MB
  echo "❌ ERROR: Unzipped size ${UNZIPPED_SIZE_MB}MB exceeds Lambda 250MB limit!"
  exit 1
fi

echo "✅ ML Layer build complete"

