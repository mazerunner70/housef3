#!/bin/bash
set -e

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
cd "$(dirname "$0")/../../infrastructure/terraform"
CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_distribution_domain)
USER_POOL_ID=$(terraform output -raw cognito_user_pool_id | cat)
CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id | cat)
cd - > /dev/null

echo "User: $USERNAME"
echo "CloudFront Domain: $CLOUDFRONT_DOMAIN"
echo "Client ID: $CLIENT_ID"
echo "User Pool ID: $USER_POOL_ID"

# Check if user exists, create if not
USER_EXISTS=$(aws cognito-idp admin-get-user --user-pool-id $USER_POOL_ID --username $USERNAME 2>/dev/null || echo "NOT_EXISTS")

if [[ $USER_EXISTS == "NOT_EXISTS" ]]; then
  echo "Creating user..."
  aws cognito-idp admin-create-user \
    --user-pool-id $USER_POOL_ID \
    --username $USERNAME \
    --temporary-password "Temp123!" \
    --message-action SUPPRESS

  # Set permanent password
  aws cognito-idp admin-set-user-password \
    --user-pool-id $USER_POOL_ID \
    --username $USERNAME \
    --password $PASSWORD \
    --permanent
else
  echo "User already exists, skipping creation"
fi

# Authenticate user and get token
echo "Authenticating user..."
AUTH_RESULT=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters USERNAME=$USERNAME,PASSWORD=$PASSWORD)

ID_TOKEN=$(echo $AUTH_RESULT | jq -r '.AuthenticationResult.IdToken')

echo "Testing CloudFront endpoint..."
echo "Making request to: https://$CLOUDFRONT_DOMAIN/api/colors"
RESPONSE=$(curl -v -s -H "Authorization: $ID_TOKEN" "https://$CLOUDFRONT_DOMAIN/api/colors")
echo "Raw response:"
echo "$RESPONSE"
echo "Attempting to parse as JSON:"
echo "$RESPONSE" | jq . || echo "Failed to parse response as JSON"

# Only continue with validation if we got a valid JSON response
if echo "$RESPONSE" | jq . >/dev/null 2>&1; then
  echo "Validating response..."

  # Extract key fields from response
  COLORS=$(echo $RESPONSE | jq -c '.colors | map(.name)')
  TOTAL=$(echo $RESPONSE | jq '.metadata.totalColors')
  USER_ID=$(echo $RESPONSE | jq -r '.user.id')

  # Validate fields
  if [[ ! -z "$COLORS" && ! -z "$TOTAL" && ! -z "$USER_ID" && "$USER_ID" != "null" ]]; then
    echo "✅ Validation successful!"
    echo "✅ User ID: $USER_ID"
    echo "✅ Total colors: $TOTAL"
    echo "✅ Colors: $COLORS"
  else
    echo "❌ Validation failed!"
    echo "Colors: $COLORS"
    echo "Total: $TOTAL"
    echo "User ID: $USER_ID"
    exit 1
  fi
else
  echo "❌ Test failed: Invalid JSON response"
  exit 1
fi

echo -e "\nAll tests passed successfully!"
exit 0 