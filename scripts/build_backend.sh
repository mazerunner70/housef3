#!/bin/bash
set -e

echo "Building backend with tests and Terraform deployment..."

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Function to handle script exit and notifications
cleanup_and_notify() {
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        "$SCRIPT_DIR/notify_build.sh" success "Backend build and deployment completed successfully!"
    else
        "$SCRIPT_DIR/notify_build.sh" fail "Backend build or deployment failed"
    fi
    exit $exit_code
}

# Set up trap to catch script exit
trap cleanup_and_notify EXIT

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
    # The EXIT trap will handle the failure notification
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

# Success notification will be handled by the EXIT trap