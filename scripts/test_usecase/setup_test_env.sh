#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Get the values from terraform output
cd "$PROJECT_ROOT/infrastructure/terraform" || exit 1
CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_distribution_domain)
COGNITO_CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
COGNITO_USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)

# Set API endpoint
API_ENDPOINT="https://${CLOUDFRONT_DOMAIN}/api"

# Export variables
export CLOUDFRONT_DOMAIN
export COGNITO_CLIENT_ID
export COGNITO_USER_POOL_ID
export API_ENDPOINT 