#!/bin/bash
set -e

# Function to handle errors
handle_error() {
  echo "❌ ERROR: $1"
  exit 1
}

# Get configuration from Terraform
echo "Getting configuration from Terraform..."
cd "$(dirname "$0")/../infrastructure/terraform"
API_ENDPOINT=$(terraform output -raw api_accounts_endpoint)
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

# Create test account name with timestamp to ensure uniqueness
TEST_ACCOUNT_NAME="Test Account $(date +%s)"
TEST_INSTITUTION="Test Bank"

# Step 1: List initial accounts
echo -e "\n1. Testing GET /accounts (initial list)"
LIST_RESPONSE=$(curl -s "$API_ENDPOINT" -H "Authorization: $TOKEN")
echo "$LIST_RESPONSE" | jq .

INITIAL_ACCOUNT_COUNT=$(echo "$LIST_RESPONSE" | jq -r '.metadata.totalAccounts // "0"')
echo "Found $INITIAL_ACCOUNT_COUNT accounts initially"

# Step 2: Create a new account
echo -e "\n2. Testing POST /accounts (create)"
CREATE_PAYLOAD="{\"accountName\":\"$TEST_ACCOUNT_NAME\", \"accountType\":\"checking\", \"institution\":\"$TEST_INSTITUTION\", \"currency\":\"USD\", \"balance\":1000, \"notes\":\"Test account created via API\"}"

echo "Create payload: $CREATE_PAYLOAD"
CREATE_RESPONSE=$(curl -s -X POST "$API_ENDPOINT" \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$CREATE_PAYLOAD")

echo "Create response:"
echo "$CREATE_RESPONSE" | jq .

ACCOUNT_ID=$(echo "$CREATE_RESPONSE" | jq -r '.account.accountId')

if [ "$ACCOUNT_ID" == "null" ] || [ -z "$ACCOUNT_ID" ]; then
  handle_error "Failed to get account ID"
fi

echo "Created account with ID: $ACCOUNT_ID"

# Step 3: List accounts after creation
echo -e "\n3. Testing GET /accounts (after creation)"
LIST_RESPONSE=$(curl -s "$API_ENDPOINT" -H "Authorization: $TOKEN")
echo "$LIST_RESPONSE" | jq .

NEW_ACCOUNT_COUNT=$(echo "$LIST_RESPONSE" | jq -r '.metadata.totalAccounts // "0"')
echo "Found $NEW_ACCOUNT_COUNT accounts after creation"

if [ "$NEW_ACCOUNT_COUNT" -le "$INITIAL_ACCOUNT_COUNT" ]; then
  handle_error "Expected more accounts after creation"
fi

# Step 4: Get the created account
echo -e "\n4. Testing GET /accounts/$ACCOUNT_ID"
GET_RESPONSE=$(curl -s "$API_ENDPOINT/$ACCOUNT_ID" -H "Authorization: $TOKEN")
echo "$GET_RESPONSE" | jq .

RETRIEVED_NAME=$(echo "$GET_RESPONSE" | jq -r '.account.accountName')
echo "Retrieved account name: $RETRIEVED_NAME"

if [ "$RETRIEVED_NAME" != "$TEST_ACCOUNT_NAME" ]; then
  handle_error "Retrieved account name doesn't match what was created"
fi

# Step 5: Update the account
echo -e "\n5. Testing PUT /accounts/$ACCOUNT_ID"
UPDATED_NAME="$TEST_ACCOUNT_NAME (Updated)"
UPDATED_BALANCE=1500
UPDATE_PAYLOAD="{\"accountName\":\"$UPDATED_NAME\", \"balance\":$UPDATED_BALANCE}"

echo "Update payload: $UPDATE_PAYLOAD"
UPDATE_RESPONSE=$(curl -s -X PUT "$API_ENDPOINT/$ACCOUNT_ID" \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$UPDATE_PAYLOAD")

echo "Update response:"
echo "$UPDATE_RESPONSE" | jq .

# Step 6: Get the updated account
echo -e "\n6. Testing GET /accounts/$ACCOUNT_ID (after update)"
GET_RESPONSE=$(curl -s "$API_ENDPOINT/$ACCOUNT_ID" -H "Authorization: $TOKEN")
echo "$GET_RESPONSE" | jq .

UPDATED_RETRIEVED_NAME=$(echo "$GET_RESPONSE" | jq -r '.account.accountName')
UPDATED_RETRIEVED_BALANCE=$(echo "$GET_RESPONSE" | jq -r '.account.balance')
echo "Retrieved updated account name: $UPDATED_RETRIEVED_NAME"
echo "Retrieved updated account balance: $UPDATED_RETRIEVED_BALANCE"

if [ "$UPDATED_RETRIEVED_NAME" != "$UPDATED_NAME" ]; then
  handle_error "Account name was not updated correctly"
fi

# Check that the account balance was updated correctly
UPDATED_BALANCE=$(echo $UPDATED_RETRIEVED_BALANCE | tr -d '"')
echo "Retrieved updated account balance: $UPDATED_BALANCE"

# Try to remove quotes and convert to a numeric value
NUMERIC_BALANCE=$(echo $UPDATED_BALANCE | tr -d '"' | bc -l)

# Check if it's close to 1500
if [ $(echo "$NUMERIC_BALANCE > 1499.99" | bc -l) -eq 1 ] && [ $(echo "$NUMERIC_BALANCE < 1500.01" | bc -l) -eq 1 ]; then
    echo "Account balance was updated correctly"
else
    echo "❌ ERROR: Account balance was not updated correctly"
    exit 1
fi

# Step 7: Delete the account
echo -e "\n7. Testing DELETE /accounts/$ACCOUNT_ID"
DELETE_RESPONSE=$(curl -s -X DELETE "$API_ENDPOINT/$ACCOUNT_ID" -H "Authorization: $TOKEN")
echo "$DELETE_RESPONSE" | jq .

DELETE_MESSAGE=$(echo "$DELETE_RESPONSE" | jq -r '.message')
echo "Delete message: $DELETE_MESSAGE"

# Step 8: Verify the account is deleted
echo -e "\n8. Testing GET /accounts/$ACCOUNT_ID (after deletion, should fail)"
GET_RESPONSE=$(curl -s "$API_ENDPOINT/$ACCOUNT_ID" -H "Authorization: $TOKEN")
echo "$GET_RESPONSE" | jq .

GET_STATUS=$(echo "$GET_RESPONSE" | jq -r '.message')
echo "Get status after deletion: $GET_STATUS"

if [[ "$GET_STATUS" != *"not found"* ]]; then
  handle_error "Account was not properly deleted"
fi

# Step 9: List accounts after deletion
echo -e "\n9. Testing GET /accounts (after deletion)"
LIST_RESPONSE=$(curl -s "$API_ENDPOINT" -H "Authorization: $TOKEN")
echo "$LIST_RESPONSE" | jq .

FINAL_ACCOUNT_COUNT=$(echo "$LIST_RESPONSE" | jq -r '.metadata.totalAccounts // "0"')
echo "Found $FINAL_ACCOUNT_COUNT accounts after deletion"

if [ "$FINAL_ACCOUNT_COUNT" -ne "$INITIAL_ACCOUNT_COUNT" ]; then
  handle_error "Account count should return to initial state after deletion"
fi

echo -e "\nAll account operation tests completed successfully! ✅" 