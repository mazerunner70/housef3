#!/bin/bash

# Check if required arguments are provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <email> <password>"
    echo "Example: $0 test@example.com 'YourPassword123!'"
    exit 1
fi

EMAIL=$1
PASSWORD=$2

# Get Cognito configuration from terraform output
cd infrastructure/terraform
USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
REGION="eu-west-2"
cd ../..

echo "Using Cognito configuration:"
echo "User Pool ID: $USER_POOL_ID"
echo "Client ID: $CLIENT_ID"
echo "Region: $REGION"
echo "-------------------"

# Create the user
echo "Creating user $EMAIL..."
aws cognito-idp sign-up \
    --client-id $CLIENT_ID \
    --username $EMAIL \
    --password $PASSWORD \
    --region $REGION

if [ $? -ne 0 ]; then
    echo "Failed to create user"
    exit 1
fi

# Confirm the user (admin confirmation)
echo "Confirming user..."
aws cognito-idp admin-confirm-sign-up \
    --user-pool-id $USER_POOL_ID \
    --username $EMAIL \
    --region $REGION

if [ $? -ne 0 ]; then
    echo "Failed to confirm user"
    exit 1
fi

# Test authentication
echo "Testing authentication..."
AUTH_RESULT=$(aws cognito-idp initiate-auth \
    --client-id $CLIENT_ID \
    --auth-flow USER_PASSWORD_AUTH \
    --auth-parameters USERNAME=$EMAIL,PASSWORD=$PASSWORD \
    --region $REGION)

if [ $? -ne 0 ]; then
    echo "Authentication failed"
    exit 1
fi

# Extract and display the access token
echo "Authentication successful!"
echo "-------------------"
echo "Access Token:"
echo $AUTH_RESULT | jq -r '.AuthenticationResult.AccessToken' 