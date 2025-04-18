#!/bin/bash
set -e

# Function to handle errors
handle_error() {
  echo "❌ ERROR: $1"
  exit 1
}

# Get configuration from Terraform
echo "Getting configuration from Terraform..."
cd "$(dirname "$0")/../../infrastructure/terraform"
CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_distribution_domain)
API_ENDPOINT="https://$CLOUDFRONT_DOMAIN/api/field-maps"
CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
cd - > /dev/null

# Load username and password from config.json
CONFIG_FILE="$(dirname "$0")/config.json"
USERNAME=$(jq -r '.username' "$CONFIG_FILE")
PASSWORD=$(jq -r '.password' "$CONFIG_FILE")

# Print configuration
echo "API Endpoint: $API_ENDPOINT"
echo "Client ID: $CLIENT_ID"
echo "User Pool ID: $USER_POOL_ID"
echo "Username: $USERNAME"

# Get authentication token
echo "Getting authentication token..."
AUTH_RESULT=$(aws --no-cli-pager cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id "$CLIENT_ID" \
  --auth-parameters USERNAME="$USERNAME",PASSWORD="$PASSWORD")

TOKEN=$(echo "$AUTH_RESULT" | jq -r '.AuthenticationResult.IdToken')
if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  handle_error "Failed to get authentication token"
fi

echo "Token received, first 20 chars: ${TOKEN:0:20}..."

# Initialize test data
TEST_FIELD_MAP='{
    "name": "Bank Statement",
    "description": "Standard bank statement field mapping",
    "mappings": [
        {
            "sourceField": "Transaction Date",
            "targetField": "date"
        },
        {
            "sourceField": "Description",
            "targetField": "description"
        },
        {
            "sourceField": "Amount",
            "targetField": "amount"
        },
        {
            "sourceField": "Transaction Type",
            "targetField": "type"
        },
        {
            "sourceField": "Balance",
            "targetField": "balance"
        }
    ]
}'

echo "Starting field map tests..."

# Test 1: Create field map
echo -e "\n1. Testing POST /field-maps (create)"
echo "Create payload: $TEST_FIELD_MAP"
CREATE_RESPONSE=$(curl -s -X POST \
    -H "Authorization: $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$TEST_FIELD_MAP" \
    "$API_ENDPOINT")

echo "Create response:"
echo "$CREATE_RESPONSE" | jq .

FIELD_MAP_ID=$(echo $CREATE_RESPONSE | jq -r '.fieldMapId')
if [ "$FIELD_MAP_ID" == "null" ] || [ -z "$FIELD_MAP_ID" ]; then
    handle_error "Failed to get field map ID"
fi

echo "Created field map with ID: $FIELD_MAP_ID"

# Test 2: Get field map
echo -e "\n2. Testing GET /field-maps/$FIELD_MAP_ID"
GET_RESPONSE=$(curl -s -X GET \
    -H "Authorization: $TOKEN" \
    "$API_ENDPOINT/$FIELD_MAP_ID")

echo "Get response:"
echo "$GET_RESPONSE" | jq .

RETRIEVED_NAME=$(echo "$GET_RESPONSE" | jq -r '.name')
if [ "$RETRIEVED_NAME" != "Bank Statement" ]; then
    handle_error "Retrieved field map name doesn't match what was created"
fi

# Test 3: List field maps
echo -e "\n3. Testing GET /field-maps"
LIST_RESPONSE=$(curl -s -X GET \
    -H "Authorization: $TOKEN" \
    "$API_ENDPOINT")

echo "List response:"
echo "$LIST_RESPONSE" | jq .

# Test 4: Update field map
echo -e "\n4. Testing PUT /field-maps/$FIELD_MAP_ID"
UPDATE_FIELD_MAP='{
    "name": "Updated Bank Statement",
    "description": "Updated standard bank statement field mapping",
    "mappings": [
        {
            "sourceField": "Date",
            "targetField": "date"
        },
        {
            "sourceField": "Transaction Description",
            "targetField": "description"
        },
        {
            "sourceField": "Transaction Amount",
            "targetField": "amount"
        },
        {
            "sourceField": "Type",
            "targetField": "type"
        },
        {
            "sourceField": "Current Balance",
            "targetField": "balance"
        }
    ]
}'

echo "Update payload: $UPDATE_FIELD_MAP"
UPDATE_RESPONSE=$(curl -s -X PUT \
    -H "Authorization: $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$UPDATE_FIELD_MAP" \
    "$API_ENDPOINT/$FIELD_MAP_ID")

echo "Update response:"
echo "$UPDATE_RESPONSE" | jq .

# Test 5: Verify update
echo -e "\n5. Testing GET /field-maps/$FIELD_MAP_ID (after update)"
VERIFY_RESPONSE=$(curl -s -X GET \
    -H "Authorization: $TOKEN" \
    "$API_ENDPOINT/$FIELD_MAP_ID")

echo "Verify response:"
echo "$VERIFY_RESPONSE" | jq .

UPDATED_NAME=$(echo "$VERIFY_RESPONSE" | jq -r '.name')
if [ "$UPDATED_NAME" != "Updated Bank Statement" ]; then
    handle_error "Field map was not updated correctly"
fi

# Test 6: Delete field map
echo -e "\n6. Testing DELETE /field-maps/$FIELD_MAP_ID"
DELETE_RESPONSE=$(curl -s -X DELETE \
    -H "Authorization: $TOKEN" \
    "$API_ENDPOINT/$FIELD_MAP_ID")

# Test 7: Verify deletion
echo -e "\n7. Testing GET /field-maps/$FIELD_MAP_ID (after deletion)"
VERIFY_DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -H "Authorization: $TOKEN" "$API_ENDPOINT/$FIELD_MAP_ID")

# Extract the status code (last line)
STATUS_CODE=$(echo "$VERIFY_DELETE_RESPONSE" | tail -n1)
# Extract the response body (all but last line)
RESPONSE_BODY=$(echo "$VERIFY_DELETE_RESPONSE" | sed '$d')

echo "Status code: $STATUS_CODE"
echo "Response body:"
echo "$RESPONSE_BODY"

if [ "$STATUS_CODE" == "404" ]; then
    echo "✅ Field map was successfully deleted"
else
    handle_error "Field map still exists after deletion (status code: $STATUS_CODE)"
fi

echo -e "\n✅ All field map tests completed successfully!"
exit 0 