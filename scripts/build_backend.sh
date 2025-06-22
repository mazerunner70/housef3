#!/bin/bash
set -e

echo "Building backend with tests and Terraform deployment..."

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Navigate to the backend directory to run tests
BACKEND_DIR="$SCRIPT_DIR/../backend"
echo "Changing to backend directory: $BACKEND_DIR"
cd "$BACKEND_DIR"

# Run backend tests first
echo "Running backend tests..."
echo "========================================================================"
./run_tests.sh

# Check if tests passed
if [ $? -ne 0 ]; then
    echo "❌ Backend tests failed! Stopping build process."
    echo "Please fix the failing tests before deploying."
    exit 1
fi

echo "✅ All backend tests passed!"
echo "========================================================================"

# Navigate to the Terraform directory for deployment
TERRAFORM_DIR="$SCRIPT_DIR/../infrastructure/terraform"
echo "Changing to Terraform directory: $TERRAFORM_DIR"
cd "$TERRAFORM_DIR"

echo "Applying Terraform changes to update Lambda functions..."
terraform init -reconfigure
terraform apply -auto-approve

echo "✅ Backend rebuild with Terraform completed successfully"
echo "========================================================================"
echo "Build Summary:"
echo "- Backend tests: PASSED"
echo "- Terraform deployment: COMPLETED"