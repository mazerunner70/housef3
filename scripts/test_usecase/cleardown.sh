#!/bin/bash
set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
CONFIG_FILE="$SCRIPT_DIR/config.json"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found at $CONFIG_FILE"
    exit 1
fi

# Read credentials from config file
USERNAME=$(jq -r '.username' "$CONFIG_FILE")
PASSWORD=$(jq -r '.password' "$CONFIG_FILE")

# Source environment variables
source "$SCRIPT_DIR/setup_test_env.sh"

# Authenticate user and get token
echo "Authenticating user..."
AUTH_RESULT=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_CLIENT_ID \
  --auth-parameters USERNAME=$USERNAME,PASSWORD=$PASSWORD)

ID_TOKEN=$(echo $AUTH_RESULT | jq -r '.AuthenticationResult.IdToken')

if [ -z "$ID_TOKEN" ] || [ "$ID_TOKEN" = "null" ]; then
    echo "Error: Failed to get ID token"
    exit 1
fi

# Get the test user's Cognito ID
echo "Fetching test user's Cognito ID..."
USER_ID=$(aws cognito-idp list-users \
    --user-pool-id $COGNITO_USER_POOL_ID \
    --filter "email = \"usecase@example.com\"" \
    --query "Users[0].Username" \
    --output text)

if [ -z "$USER_ID" ] || [ "$USER_ID" = "None" ]; then
    echo "Error: Could not find test user in Cognito"
    exit 1
fi

echo "Cleaning up resources for user: $USER_ID"

# Delete all accounts and their files
echo "Deleting all accounts and their files..."
DELETE_RESPONSE=$(curl -s -X DELETE "${API_ENDPOINT}/accounts" \
  -H "Authorization: Bearer ${ID_TOKEN}")
echo "Delete response: $DELETE_RESPONSE"

echo "Cleanup complete!" 