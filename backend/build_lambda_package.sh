#!/bin/bash

set -e          # Exit on any error
set -u          # Exit on undefined variables  
set -o pipefail # Exit on pipe failures

echo "=== Lambda Package Build Script ==="
echo "=== Build Validation Phase ==="
echo "Current working directory: $(pwd)"

# Critical validation checks
echo "Checking prerequisites..."
if [ ! -f "requirements-lambda.txt" ]; then
  echo "❌ CRITICAL ERROR: requirements-lambda.txt not found"
  exit 1
fi

if [ ! -d "venv" ]; then
  echo "❌ CRITICAL ERROR: venv directory not found"
  exit 1
fi

if [ ! -f "venv/bin/activate" ]; then
  echo "❌ CRITICAL ERROR: venv/bin/activate not found"
  exit 1
fi

if [ ! -d "src" ]; then
  echo "❌ CRITICAL ERROR: src directory not found"
  exit 1
fi

echo "✅ Prerequisites validated"

echo "=== Version Management Phase ==="
# Build number tracking
BUILD_NUMBER_FILE=".build_number"
VERSION_FILE=".current_version"

# Base semantic version (can be overridden with environment variable)
BASE_VERSION="${SEMVER_BASE:-v1.0.0}"

# Read and increment build number
if [ -f "$BUILD_NUMBER_FILE" ]; then
    BUILD_NUMBER=$(cat "$BUILD_NUMBER_FILE")
    echo "Current build number: $BUILD_NUMBER"
else
    BUILD_NUMBER=0
    echo "Initializing build number to: $BUILD_NUMBER"
fi

# Increment build number
BUILD_NUMBER=$((BUILD_NUMBER + 1))
echo "New build number: $BUILD_NUMBER"

# Create full version with build number
FULL_VERSION="${BASE_VERSION}.${BUILD_NUMBER}"
echo "Full version: $FULL_VERSION"

# Save build number and version
echo "$BUILD_NUMBER" > "$BUILD_NUMBER_FILE"
echo "$FULL_VERSION" > "$VERSION_FILE"

# Export for potential use by other scripts
export BUILD_NUMBER
export FULL_VERSION

echo "✅ Version management completed: $FULL_VERSION"

echo "=== Testing Phase ==="
# Create test venv and install all dependencies for testing
echo "Creating test environment..."
python3 -m venv .venv_test
source .venv_test/bin/activate
pip install -r requirements.txt

# Run tests
echo "Running tests..."
chmod +x run_tests.sh && ./run_tests.sh
if [ $? -ne 0 ]; then
  echo "❌ CRITICAL ERROR: Tests failed"
  exit 1
fi
echo "✅ Tests passed"

# Deactivate test venv
deactivate

echo "=== Build Phase ==="
# Setup build
rm -rf build
mkdir -p build

# Activate existing venv and install Lambda runtime dependencies to build directory
echo "Activating production venv..."
source venv/bin/activate
if [ $? -ne 0 ]; then
  echo "❌ CRITICAL ERROR: Failed to activate venv"
  exit 1
fi

echo "✅ venv activated successfully"
echo "Python version: $(python --version)"
echo "pip version: $(pip --version)"
echo "Installing Lambda dependencies..."
pip install \
  -r requirements-lambda.txt \
  -t build/ \
  --platform manylinux2014_x86_64 \
  --python-version 3.12 \
  --only-binary=:all:

if [ $? -ne 0 ]; then
  echo "❌ CRITICAL ERROR: Failed to install Lambda dependencies"
  exit 1
fi
echo "✅ Dependencies installed successfully"

# Copy source code
echo "Copying source code..."
cp -r src/* build/
if [ $? -ne 0 ]; then
  echo "❌ CRITICAL ERROR: Failed to copy source code"
  exit 1
fi
echo "✅ Source code copied successfully"

# Clean up unnecessary files
echo "Cleaning up unnecessary files..."
find build -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find build -type f -name "*.pyc" -delete
find build -type f -name "*.pyo" -delete
find build -type f -name "*.dll" -delete
find build -type f -name "*.exe" -delete
find build -type f -name "*.bat" -delete
find build -type f -name "*.sh" -delete
find build -type f -name "*.txt" -delete
find build -type f -name "*.md" -delete
find build -type f -name "*.rst" -delete
find build -type f -name "*.html" -delete
find build -type f -name "*.css" -delete
find build -type f -name "*.js" -delete
find build -type f -name "*.json" -delete
find build -type f -name "*.xml" -delete
find build -type f -name "*.yaml" -delete
find build -type f -name "*.yml" -delete
find build -type f -name "*.ini" -delete
find build -type f -name "*.cfg" -delete
find build -type f -name "*.conf" -delete
find build -type f -name "*.log" -delete
find build -type f -name "*.dat" -delete
find build -type f -name "*.db" -delete
find build -type f -name "*.sqlite" -delete
find build -type f -name "*.sqlite3" -delete
find build -type f -name "*.pdb" -delete
find build -type f -name "*.pyd" -delete
find build -type f -name "*.pyi" -delete
find build -type f -name "*.pyx" -delete
find build -type f -name "*.pxd" -delete
find build -type f -name "*.pxi" -delete
find build -type f -name "*.h" -delete
find build -type f -name "*.c" -delete
find build -type f -name "*.cpp" -delete
find build -type f -name "*.cc" -delete
find build -type f -name "*.cxx" -delete
find build -type f -name "*.hpp" -delete
find build -type f -name "*.hh" -delete
find build -type f -name "*.hxx" -delete
find build -type f -name "*.f" -delete
find build -type f -name "*.f90" -delete
find build -type f -name "*.f95" -delete
find build -type f -name "*.f03" -delete
find build -type f -name "*.f08" -delete
find build -type f -name "*.for" -delete
find build -type f -name "*.ftn" -delete

echo "=== Package Creation Phase ==="
# Create deployment package
echo "Creating deployment package..."
cd build
zip -r ../lambda_deploy.zip .
if [ $? -ne 0 ]; then
  echo "❌ CRITICAL ERROR: Failed to create deployment package"
  exit 1
fi
cd ..

# Validate package was created
if [ ! -f "lambda_deploy.zip" ]; then
  echo "❌ CRITICAL ERROR: lambda_deploy.zip was not created"
  exit 1
fi

# Check package size (should be reasonable, not too small or huge)
PACKAGE_SIZE=$(stat -c%s "lambda_deploy.zip")
if [ "$PACKAGE_SIZE" -lt 1000000 ]; then  # Less than 1MB
  echo "⚠️  WARNING: Package size is only ${PACKAGE_SIZE} bytes - seems too small"
fi
if [ "$PACKAGE_SIZE" -gt 50000000 ]; then  # More than 50MB
  echo "⚠️  WARNING: Package size is ${PACKAGE_SIZE} bytes - seems too large"
fi

echo "✅ Deployment package created successfully (${PACKAGE_SIZE} bytes)"

# Cleanup test environment only (retain build directory for inspection)
rm -rf .venv_test

echo "=== Build Summary ==="
echo "✅ All phases completed successfully!"
echo "📍 Working directory: $(pwd)"
echo "📦 Package location: $(pwd)/lambda_deploy.zip"
echo "📁 Build directory retained at: $(pwd)/build/"
echo "🔍 Build contents preview:"
ls -la build/ | head -10

echo "=== Lambda Package Build Complete ==="