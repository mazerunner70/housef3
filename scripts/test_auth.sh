#!/bin/bash

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed. Please install jq first."
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CONFIG_FILE="$SCRIPT_DIR/config.json"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found at $CONFIG_FILE"
    exit 1
fi

# Read credentials from config file
USERNAME=$(jq -r '.username' "$CONFIG_FILE")
PASSWORD=$(jq -r '.password' "$CONFIG_FILE")

# Validate credentials were read successfully
if [ -z "$USERNAME" ] || [ "$USERNAME" = "null" ]; then
    echo "Error: Username not found in config file"
    exit 1
fi

if [ -z "$PASSWORD" ] || [ "$PASSWORD" = "null" ]; then
    echo "Error: Password not found in config file"
    exit 1
fi

# Get the values from terraform output
cd infrastructure/terraform || exit 1
API_ENDPOINT=$(terraform output -raw api_endpoint)
CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_distribution_domain)
CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)

echo "Using user: $USERNAME"
echo "API Endpoint: $API_ENDPOINT"
echo "CloudFront Domain: $CLOUDFRONT_DOMAIN"
echo "Client ID: $CLIENT_ID"
echo "User Pool ID: $USER_POOL_ID"

# Function to check if user exists
check_user_exists() {
    aws cognito-idp admin-get-user \
        --user-pool-id "$USER_POOL_ID" \
        --username "$USERNAME" > /dev/null 2>&1
    return $?
}

# Function to create a test user
create_test_user() {
    echo "Creating test user..."
    aws cognito-idp admin-create-user \
        --user-pool-id "$USER_POOL_ID" \
        --username "$USERNAME" \
        --temporary-password "Test123!" \
        --user-attributes Name=email,Value="$USERNAME" Name=email_verified,Value=true \
        --message-action SUPPRESS

    if [ $? -ne 0 ]; then
        echo "Error: Failed to create user"
        exit 1
    fi
    
    # Set permanent password
    aws cognito-idp admin-set-user-password \
        --user-pool-id "$USER_POOL_ID" \
        --username "$USERNAME" \
        --password "$PASSWORD" \
        --permanent

    if [ $? -ne 0 ]; then
        echo "Error: Failed to set user password"
        exit 1
    fi
}

# Function to get authentication token
get_auth_token() {
    echo "Getting authentication token..."
    TOKEN=$(aws cognito-idp initiate-auth \
        --client-id "$CLIENT_ID" \
        --auth-flow USER_PASSWORD_AUTH \
        --auth-parameters USERNAME="$USERNAME",PASSWORD="$PASSWORD" \
        --query 'AuthenticationResult.IdToken' \
        --output text)

    if [ $? -ne 0 ] || [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
        echo "Error: Failed to obtain authentication token"
        exit 1
    fi

    echo "Token obtained successfully"
}

# Function to check response
check_response() {
    local response=$1
    local endpoint_name=$2
    
    # Check if response is valid JSON
    if ! echo "$response" | jq . >/dev/null 2>&1; then
        echo "Error: Invalid JSON response from $endpoint_name"
        return 1
    fi
    
    # Check if response contains colors array and user ID
    if ! echo "$response" | jq -e '.colors and (.colors | type=="array") and (.colors | length>0) and .user' >/dev/null 2>&1; then
        echo "Error: Response from $endpoint_name does not contain expected colors array and user ID"
        return 1
    fi
    
    echo "Success: Received valid response from $endpoint_name"
    return 0
}

# Check if user exists, create if not
if ! check_user_exists; then
    create_test_user
else
    echo "User already exists, skipping creation"
fi

# Get the authentication token
get_auth_token

# Test direct API Gateway endpoint
echo -e "\n****************************Testing direct API Gateway endpoint..."
API_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_ENDPOINT")
echo "API Gateway Response:"
echo "$API_RESPONSE" | jq .
check_response "$API_RESPONSE" "API Gateway" || exit 1

# Test CloudFront endpoint
echo -e "\n****************************Testing CloudFront endpoint..."
CF_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" "https://$CLOUDFRONT_DOMAIN/api/colors")
echo "CloudFront Raw Response:"
echo "$CF_RESPONSE"
echo -e "\nCloudFront Response (parsed):"
echo "$CF_RESPONSE" | jq . || echo "Failed to parse response as JSON"
check_response "$CF_RESPONSE" "CloudFront" || exit 1

echo -e "\nAll tests passed successfully!"
exit 0 