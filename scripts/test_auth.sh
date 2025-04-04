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
cd infrastructure/terraform || exit 1
API_ENDPOINT=$(terraform output -raw api_endpoint)
CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_distribution_domain)
CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)

echo "User: $USERNAME"
echo "API Endpoint: $API_ENDPOINT"
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

echo "Testing direct API Gateway endpoint..."
DIRECT_RESPONSE=$(curl -s -H "Authorization: $ID_TOKEN" $API_ENDPOINT)
echo "API Gateway response:"
echo $DIRECT_RESPONSE | jq .

echo "Testing CloudFront endpoint..."
CF_RESPONSE=$(curl -v -s -H "Authorization: $ID_TOKEN" https://$CLOUDFRONT_DOMAIN/colors)
echo "CloudFront response:"
echo $CF_RESPONSE | jq .

# Validate responses
echo "Validating responses..."

# Extract key fields from responses to compare
API_COLORS=$(echo $DIRECT_RESPONSE | jq -c '.colors | map(.name)')
CF_COLORS=$(echo $CF_RESPONSE | jq -c '.colors | map(.name)')

API_TOTAL=$(echo $DIRECT_RESPONSE | jq '.metadata.totalColors')
CF_TOTAL=$(echo $CF_RESPONSE | jq '.metadata.totalColors')

API_USER_ID=$(echo $DIRECT_RESPONSE | jq -r '.user.id')
CF_USER_ID=$(echo $CF_RESPONSE | jq -r '.user.id')

# Compare key fields
if [[ "$API_COLORS" == "$CF_COLORS" && "$API_TOTAL" == "$CF_TOTAL" && "$API_USER_ID" == "$CF_USER_ID" ]]; then
  echo "✅ Validation successful! CloudFront is correctly forwarding to API Gateway."
  echo "✅ User ID: $CF_USER_ID"
  echo "✅ Total colors: $CF_TOTAL"
  echo "✅ Colors: $CF_COLORS"
else
  echo "❌ Validation failed! Responses don't match."
  echo "API Colors: $API_COLORS"
  echo "CloudFront Colors: $CF_COLORS"
  echo "API Total: $API_TOTAL"
  echo "CloudFront Total: $CF_TOTAL"
  echo "API User ID: $API_USER_ID"
  echo "CloudFront User ID: $CF_USER_ID"
  exit 1
fi

echo -e "\nAll tests passed successfully!"
exit 0 