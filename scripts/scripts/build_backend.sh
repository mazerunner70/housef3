#!/bin/bash
set -e

echo "Rebuilding backend with Terraform..."

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Navigate to the Terraform directory, which is two levels up and then into infrastructure/terraform
TERRAFORM_DIR="$SCRIPT_DIR/../../infrastructure/terraform"

echo "Changing to directory: $TERRAFORM_DIR"
cd "$TERRAFORM_DIR"

echo "Applying Terraform changes to update Lambda functions..."
terraform init -reconfigure
terraform apply -auto-approve

echo "Backend rebuild with Terraform completed successfully"
# Go back to the original project root if needed, or simply exit.
# For now, let's assume operations are done within terraform dir or it's not critical to return.
# cd "$SCRIPT_DIR/../.." 