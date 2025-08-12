#!/bin/bash
set -e

# Script to build the frontend and deploy to S3

# Get directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Navigate to project root
cd "$PROJECT_ROOT"

# Update environment variables from Terraform outputs
echo "Updating frontend environment variables..."
bash "$SCRIPT_DIR/update-frontend-env.sh" "$SCRIPT_DIR" "$PROJECT_ROOT"

# Navigate to frontend directory
cd frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

# Run frontend unit tests before building
echo "Running frontend unit tests..."
bash "$PROJECT_ROOT/frontend/fe_unit_tests.sh"

# Build the application
echo "Building frontend application..."
npm run build

# Get S3 bucket name from Terraform output
cd "$PROJECT_ROOT/infrastructure/terraform"
S3_BUCKET=$(terraform output -raw frontend_bucket_name)
CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_distribution_domain)
CLOUDFRONT_ID=$(terraform output -raw cloudfront_distribution_id)

# Deploy to S3
echo "Deploying frontend to S3 bucket: $S3_BUCKET"
cd "$PROJECT_ROOT/frontend/dist"
aws s3 sync . "s3://$S3_BUCKET" --delete

# Invalidate CloudFront cache
echo "Invalidating CloudFront cache..."
aws cloudfront create-invalidation --distribution-id $CLOUDFRONT_ID --paths "/*" --no-cli-pager

echo "Frontend build and deployment complete!"
echo "Your application is available at: https://$CLOUDFRONT_DOMAIN" 