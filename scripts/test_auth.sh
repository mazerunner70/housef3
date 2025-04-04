#!/bin/bash

# Default values
DEFAULT_USERNAME="testuser@example.com"
DEFAULT_PASSWORD="Test123!@"

# Get the values from terraform output
cd infrastructure/terraform || exit 1
API_ENDPOINT=$(terraform output -raw api_endpoint)
CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)

echo "Using default test user: $DEFAULT_USERNAME"
echo "API Endpoint: $API_ENDPOINT"
echo "Client ID: $CLIENT_ID"
echo "User Pool ID: $USER_POOL_ID"

# Function to check if user exists
check_user_exists() {
    aws cognito-idp admin-get-user \
        --user-pool-id "$USER_POOL_ID" \
        --username "$DEFAULT_USERNAME" > /dev/null 2>&1
    return $?
}

# Function to create a test user
create_test_user() {
    echo "Creating test user..."
    aws cognito-idp admin-create-user \
        --user-pool-id "$USER_POOL_ID" \
        --username "$DEFAULT_USERNAME" \
        --temporary-password "Test123!" \
        --user-attributes Name=email,Value="$DEFAULT_USERNAME" Name=email_verified,Value=true \
        --message-action SUPPRESS
    
    # Set permanent password
    aws cognito-idp admin-set-user-password \
        --user-pool-id "$USER_POOL_ID" \
        --username "$DEFAULT_USERNAME" \
        --password "$DEFAULT_PASSWORD" \
        --permanent
}

# Function to get authentication token
get_auth_token() {
    echo "Getting authentication token..."
    TOKEN=$(aws cognito-idp initiate-auth \
        --client-id "$CLIENT_ID" \
        --auth-flow USER_PASSWORD_AUTH \
        --auth-parameters USERNAME="$DEFAULT_USERNAME",PASSWORD="$DEFAULT_PASSWORD" \
        --query 'AuthenticationResult.IdToken' \
        --output text)
    echo "Token obtained"
}

# Check if user exists, create if not
if ! check_user_exists; then
    create_test_user
else
    echo "User already exists, skipping creation"
fi

# Get the authentication token
get_auth_token

# Test the API endpoint
echo "Testing API endpoint..."
curl -v -H "Authorization: $TOKEN" "$API_ENDPOINT" 