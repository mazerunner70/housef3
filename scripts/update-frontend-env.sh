#!/bin/bash
set -e

# Navigate to the Terraform directory
cd "$(dirname "$0")/../infrastructure/terraform"

# Extract Cognito configuration variables
COGNITO_USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
COGNITO_CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
AWS_REGION=$(terraform output -raw aws_region 2>/dev/null || echo "eu-west-2")
CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_domain 2>/dev/null || echo "d2q06gtsnbb6iy.cloudfront.net")

# Create or update the .env.local file
ENV_FILE="../../frontend/.env.local"

echo "Updating frontend environment variables..."
cat > "$ENV_FILE" << EOF
VITE_COGNITO_USER_POOL_ID=${COGNITO_USER_POOL_ID}
VITE_COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}
VITE_AWS_REGION=${AWS_REGION}
VITE_CLOUDFRONT_DOMAIN=${CLOUDFRONT_DOMAIN}
EOF

echo "Frontend environment variables updated successfully."
echo "Variables set:"
echo "VITE_COGNITO_USER_POOL_ID: ${COGNITO_USER_POOL_ID}"
echo "VITE_COGNITO_CLIENT_ID: ${COGNITO_CLIENT_ID}"
echo "VITE_AWS_REGION: ${AWS_REGION}"
echo "VITE_CLOUDFRONT_DOMAIN: ${CLOUDFRONT_DOMAIN}" 