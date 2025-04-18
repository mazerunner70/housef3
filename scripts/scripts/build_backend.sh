#!/bin/bash
set -e

echo "Rebuilding backend with Terraform..."

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Navigate to the Terraform directory
cd "$PROJECT_ROOT/infrastructure/terraform"

echo "Applying Terraform changes to update Lambda functions..."
terraform init -reconfigure
terraform apply -auto-approve

echo "Backend rebuild with Terraform completed successfully"
cd "$PROJECT_ROOT" 