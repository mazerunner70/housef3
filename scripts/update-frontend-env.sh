#!/bin/bash
set -e

# Accept SCRIPT_DIR and PROJECT_ROOT as arguments, fallback to calculated values
SCRIPT_DIR="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
PROJECT_ROOT="${2:-$(cd "$SCRIPT_DIR/.." && pwd)}"

# Navigate to the Terraform directory
cd "$PROJECT_ROOT/infrastructure/terraform"

# Extract Cognito configuration variables
COGNITO_USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
COGNITO_CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
AWS_REGION=$(terraform output -raw aws_region 2>/dev/null || echo "eu-west-2")
CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_distribution_domain 2>/dev/null || echo "d2q06gtsnbb6iy.cloudfront.net")
API_ENDPOINT="https://${CLOUDFRONT_DOMAIN}"

# Create or update the development .env.local file
DEV_ENV_FILE="$PROJECT_ROOT/frontend/.env.local"

echo "Updating frontend development environment variables..."
cat > "$DEV_ENV_FILE" << EOF
VITE_COGNITO_USER_POOL_ID=${COGNITO_USER_POOL_ID}
VITE_COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}
VITE_AWS_REGION=${AWS_REGION}
VITE_CLOUDFRONT_DOMAIN=${CLOUDFRONT_DOMAIN}
VITE_API_ENDPOINT=${API_ENDPOINT}
EOF

# Create or update the production .env.production file
PROD_ENV_FILE="$PROJECT_ROOT/frontend/.env.production"

echo "Updating frontend production environment variables..."
cat > "$PROD_ENV_FILE" << EOF
VITE_COGNITO_USER_POOL_ID=${COGNITO_USER_POOL_ID}
VITE_COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}
VITE_AWS_REGION=${AWS_REGION}
VITE_CLOUDFRONT_DOMAIN=${CLOUDFRONT_DOMAIN}
VITE_API_ENDPOINT=${API_ENDPOINT}
EOF

echo "Frontend environment variables updated successfully."
echo "Variables set:"
echo "VITE_COGNITO_USER_POOL_ID: ${COGNITO_USER_POOL_ID}"
echo "VITE_COGNITO_CLIENT_ID: ${COGNITO_CLIENT_ID}"
echo "VITE_AWS_REGION: ${AWS_REGION}"
echo "VITE_CLOUDFRONT_DOMAIN: ${CLOUDFRONT_DOMAIN}"
echo "VITE_API_ENDPOINT: ${API_ENDPOINT}" 