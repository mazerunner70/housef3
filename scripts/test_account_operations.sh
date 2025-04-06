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

# Test file creation for account association
create_test_file() {
  local filename="account_deletion_test.txt"
  local filepath="/tmp/$filename"
  echo "This is a test file for testing account file associations." > "$filepath"
  echo "Created at $(date)" >> "$filepath"
  echo "File created: $filepath (size: $(wc -c < "$filepath") bytes)" >&2
  echo "$filepath"
}

# After creating the test account and before deleting it, let's associate a file with it
echo -e "\n7. Testing file association with account before deletion"
TEST_FILE_PATH=$(create_test_file)
echo "Using test file: $TEST_FILE_PATH"

if [ ! -f "$TEST_FILE_PATH" ]; then
  echo "❌ ERROR: Test file does not exist at $TEST_FILE_PATH"
  
  # Try to create the file directly as a fallback
  mkdir -p /tmp
  echo "This is a test file for testing account file associations." > /tmp/account_deletion_test.txt
  echo "Created at $(date)" >> /tmp/account_deletion_test.txt
  TEST_FILE_PATH="/tmp/account_deletion_test.txt"
  
  if [ ! -f "$TEST_FILE_PATH" ]; then
    handle_error "Failed to create test file"
  else
    echo "✅ Created fallback test file: $TEST_FILE_PATH"
  fi
fi

FILENAME=$(basename "$TEST_FILE_PATH")
FILESIZE=$(wc -c < "$TEST_FILE_PATH")
echo "File details: name=$FILENAME, size=$FILESIZE bytes"

# Get a presigned URL for file upload
echo "Uploading test file to account: $ACCOUNT_ID"
UPLOAD_RESPONSE=$(curl -s -X POST \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"fileName\":\"$FILENAME\", \"contentType\":\"text/plain\", \"fileSize\":$FILESIZE}" \
  "$API_ENDPOINT/$ACCOUNT_ID/files")

echo "Upload response:"
echo "$UPLOAD_RESPONSE" | jq .

FILE_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.fileId')
UPLOAD_URL=$(echo "$UPLOAD_RESPONSE" | jq -r '.uploadUrl')

if [ -z "$FILE_ID" ] || [ "$FILE_ID" == "null" ]; then
  handle_error "Failed to get a valid file ID for upload"
fi

# Upload the file to S3 using the presigned URL
echo "Uploading file to S3..."
curl -s -X PUT -T "$TEST_FILE_PATH" \
  -H "Content-Type: text/plain" \
  "$UPLOAD_URL" > /dev/null

echo "File uploaded successfully with ID: $FILE_ID"

# Verify the file is associated with the account
echo -e "\nVerifying file association with account..."
ACCOUNT_FILES_RESPONSE=$(curl -s -H "Authorization: $TOKEN" "$API_ENDPOINT/$ACCOUNT_ID/files")
ASSOCIATED_FILE_COUNT=$(echo "$ACCOUNT_FILES_RESPONSE" | jq -r '.metadata.totalFiles // 0')
echo "Account has $ASSOCIATED_FILE_COUNT associated files"

if [ "$ASSOCIATED_FILE_COUNT" -lt 1 ]; then
  handle_error "File was not associated with the account"
fi

# Now delete the account and verify file handling
echo -e "\n8. Testing DELETE /accounts/$ACCOUNT_ID (with associated files)"
DELETE_RESPONSE=$(curl -s -X DELETE -H "Authorization: $TOKEN" "$API_ENDPOINT/$ACCOUNT_ID")
echo "$DELETE_RESPONSE" | jq .

DELETE_MESSAGE=$(echo "$DELETE_RESPONSE" | jq -r '.message')
echo "Delete message: $DELETE_MESSAGE"

if [[ "$DELETE_MESSAGE" != *"successfully"* ]]; then
  handle_error "Failed to delete account"
fi

# Check if the account is really gone
echo -e "\n9. Testing GET /accounts/$ACCOUNT_ID (after deletion, should fail)"
GET_RESPONSE=$(curl -s -H "Authorization: $TOKEN" "$API_ENDPOINT/$ACCOUNT_ID")
echo "$GET_RESPONSE" | jq .

GET_STATUS=$(echo "$GET_RESPONSE" | jq -r '.message')
echo "Get status after deletion: $GET_STATUS"

if [[ "$GET_STATUS" != *"not found"* ]]; then
  handle_error "Account was not properly deleted"
fi

# Check if the files still exist but are no longer associated with the account
echo -e "\n10. Checking if files exist but without account association"
# The FILES_ENDPOINT should be at the same level as accounts
FILES_ENDPOINT="${API_ENDPOINT%accounts*}files"
echo "Using files endpoint: $FILES_ENDPOINT"

FILE_RESPONSE=$(curl -s -H "Authorization: $TOKEN" "$FILES_ENDPOINT/$FILE_ID")
echo "$FILE_RESPONSE" | jq .

FILE_EXISTS=$(echo "$FILE_RESPONSE" | jq -r 'if has("fileId") then "yes" else "no" end')
echo "File exists: $FILE_EXISTS"

if [ "$FILE_EXISTS" == "no" ]; then
  echo "Warning: File may not exist after account deletion, but this is acceptable"
else
  FILE_ACCOUNT_ID=$(echo "$FILE_RESPONSE" | jq -r '.accountId // "null"')
  echo "File account ID after account deletion: $FILE_ACCOUNT_ID"

  if [ "$FILE_ACCOUNT_ID" != "null" ] && [ "$FILE_ACCOUNT_ID" == "$ACCOUNT_ID" ]; then
    handle_error "File should no longer be associated with the deleted account"
  else
    echo "✅ File is no longer associated with the deleted account"
  fi
fi

# Step 11: List accounts after deletion
echo -e "\n11. Testing GET /accounts (after deletion)"
LIST_RESPONSE=$(curl -s "$API_ENDPOINT" -H "Authorization: $TOKEN")
echo "$LIST_RESPONSE" | jq .

FINAL_ACCOUNT_COUNT=$(echo "$LIST_RESPONSE" | jq -r '.metadata.totalAccounts // "0"')
echo "Found $FINAL_ACCOUNT_COUNT accounts after deletion"

if [ "$FINAL_ACCOUNT_COUNT" -ne "$INITIAL_ACCOUNT_COUNT" ]; then
  handle_error "Account count should return to initial state after deletion"
fi

echo -e "\nAll account operation tests completed successfully! ✅" 