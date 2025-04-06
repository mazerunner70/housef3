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
API_ENDPOINT=$(terraform output -raw api_files_endpoint)
CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_distribution_domain)
CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
FILE_STORAGE_BUCKET=$(terraform output -raw file_storage_bucket_name)
cd - > /dev/null

# Load username and password from config.json
CONFIG_FILE="$(dirname "$0")/config.json"
USERNAME=$(jq -r '.username' "$CONFIG_FILE")
PASSWORD=$(jq -r '.password' "$CONFIG_FILE")

# Print configuration
echo "API Endpoint: $API_ENDPOINT"
echo "CloudFront Domain: $CLOUDFRONT_DOMAIN"
echo "Client ID: $CLIENT_ID"
echo "User Pool ID: $USER_POOL_ID"
echo "Storage Bucket: $FILE_STORAGE_BUCKET"
echo "Username: $USERNAME"

# Get authentication token directly
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

# Create a test file
TEST_FILE="/tmp/test_file.txt"
echo "This is a test file for API operations." > "$TEST_FILE"
FILE_SIZE=$(stat -c%s "$TEST_FILE")
echo "Created test file: $TEST_FILE (size: $FILE_SIZE bytes)"

# Step 1: List files (initial)
echo -e "\n1. Testing GET /files (initial list)"
LIST_RESPONSE=$(curl -s "$API_ENDPOINT" -H "Authorization: $TOKEN")
echo "$LIST_RESPONSE" | jq .

FILE_COUNT=$(echo "$LIST_RESPONSE" | jq -r '.metadata.totalFiles // "0"')
echo "Found $FILE_COUNT files"

# Get a valid account ID from the accounts endpoint
echo -e "\nGetting a valid account ID..."
ACCOUNTS_ENDPOINT="${API_ENDPOINT%files}/accounts"
ACCOUNT_LIST_RESPONSE=$(curl -s -H "Authorization: $TOKEN" "$ACCOUNTS_ENDPOINT")
echo "Accounts response:"
echo "$ACCOUNT_LIST_RESPONSE" | jq '.accounts[0]'

# Extract the first account ID
ACCOUNT_ID=$(echo "$ACCOUNT_LIST_RESPONSE" | jq -r '.accounts[0].accountId')
ACCOUNT_NAME=$(echo "$ACCOUNT_LIST_RESPONSE" | jq -r '.accounts[0].accountName')

if [ -z "$ACCOUNT_ID" ] || [ "$ACCOUNT_ID" = "null" ]; then
  echo "No real account found, creating a test account ID instead"
  TEST_ACCOUNT_ID="acc-$(date +%s)"
  echo "Created test account ID: $TEST_ACCOUNT_ID"
else
  TEST_ACCOUNT_ID="$ACCOUNT_ID"
  echo "Using real account ID: $TEST_ACCOUNT_ID (name: $ACCOUNT_NAME)"
fi

# Step 2: Get upload URL
echo -e "\n2. Testing POST /files/upload"
UPLOAD_ENDPOINT="${API_ENDPOINT%/files}/files/upload"
UPLOAD_PAYLOAD="{\"fileName\":\"test_file.txt\", \"contentType\":\"text/plain\", \"fileSize\": $FILE_SIZE, \"accountId\": \"$TEST_ACCOUNT_ID\"}"

echo "Upload endpoint: $UPLOAD_ENDPOINT"
echo "Upload payload: $UPLOAD_PAYLOAD"
echo "Authorization header: Authorization: ${TOKEN:0:20}..."

UPLOAD_RESPONSE=$(curl -s -X POST "$UPLOAD_ENDPOINT" \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$UPLOAD_PAYLOAD")

echo "Upload response:"
echo "$UPLOAD_RESPONSE" | jq .

FILE_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.fileId')
UPLOAD_URL=$(echo "$UPLOAD_RESPONSE" | jq -r '.uploadUrl')
PROCESSING_STATUS=$(echo "$UPLOAD_RESPONSE" | jq -r '.processingStatus')
FILE_FORMAT=$(echo "$UPLOAD_RESPONSE" | jq -r '.fileFormat')

if [ "$FILE_ID" == "null" ] || [ -z "$FILE_ID" ]; then
  handle_error "Failed to get file ID"
fi

echo "Received file ID: $FILE_ID"
echo "Processing status: $PROCESSING_STATUS"
echo "File format: $FILE_FORMAT"

# Step 3: Upload file
echo -e "\n3. Testing file upload using pre-signed URL"
curl -s -X PUT "$UPLOAD_URL" \
  -H "Content-Type: text/plain" \
  --data-binary @"$TEST_FILE"

echo "File uploaded successfully"

# Step 4: List files (after upload)
echo -e "\n4. Testing GET /files (after upload)"
LIST_RESPONSE=$(curl -s "$API_ENDPOINT" -H "Authorization: $TOKEN")
echo "$LIST_RESPONSE" | jq .

FILE_COUNT=$(echo "$LIST_RESPONSE" | jq -r '.metadata.totalFiles // "0"')
echo "Found $FILE_COUNT files"

# Step 5: Query files by account ID 
echo -e "\n5. Testing GET /files?accountId=$TEST_ACCOUNT_ID"
ACCOUNT_LIST_RESPONSE=$(curl -s "$API_ENDPOINT?accountId=$TEST_ACCOUNT_ID" -H "Authorization: $TOKEN")
echo "$ACCOUNT_LIST_RESPONSE" | jq .

ACCOUNT_FILE_COUNT=$(echo "$ACCOUNT_LIST_RESPONSE" | jq -r '.metadata.totalFiles // "0"')
echo "Found $ACCOUNT_FILE_COUNT files for account $TEST_ACCOUNT_ID"

# Step 5b: Test the files/account/{accountId} endpoint
echo -e "\n5b. Testing GET /files/account/$TEST_ACCOUNT_ID"
ACCOUNT_FILES_ENDPOINT="${API_ENDPOINT%/files}/files/account/$TEST_ACCOUNT_ID"
echo "Account files endpoint: $ACCOUNT_FILES_ENDPOINT"

ACCOUNT_FILES_RESPONSE=$(curl -s "$ACCOUNT_FILES_ENDPOINT" -H "Authorization: $TOKEN")
echo "$ACCOUNT_FILES_RESPONSE" | jq .

# Check if we have valid response with files for this account
FILE_COUNT_FROM_ENDPOINT=$(echo "$ACCOUNT_FILES_RESPONSE" | jq -r '.files | length // 0')
echo "Found $FILE_COUNT_FROM_ENDPOINT files via direct endpoint"

if [[ $FILE_COUNT_FROM_ENDPOINT -gt 0 ]]; then
  echo "✅ Successfully validated GET /files/account/{accountId} endpoint"
else
  echo "⚠️ WARNING: Expected files for account $TEST_ACCOUNT_ID, but found none"
fi

# Step 5c: Test trying to upload to an invalid account
echo -e "\n5c. Testing POST /files/upload with invalid account ID"
INVALID_ACCOUNT_ID="acc-invalid-$(date +%s)"
UPLOAD_INVALID_PAYLOAD="{\"fileName\":\"invalid_test.txt\", \"contentType\":\"text/plain\", \"fileSize\": $FILE_SIZE, \"accountId\": \"$INVALID_ACCOUNT_ID\"}"

INVALID_UPLOAD_RESPONSE=$(curl -s -X POST "$UPLOAD_ENDPOINT" \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$UPLOAD_INVALID_PAYLOAD")

echo "Upload response for invalid account:"
echo "$INVALID_UPLOAD_RESPONSE" | jq .

INVALID_RESPONSE_STATUS=$(echo "$INVALID_UPLOAD_RESPONSE" | jq -r '.message // ""')
if [[ "$INVALID_RESPONSE_STATUS" == *"not found"* ]]; then
  echo "✅ Successfully validated invalid account ID check"
else
  echo "⚠️ WARNING: Expected error for invalid account ID, but received different response"
fi

# Step 6: Get download URL
echo -e "\n6. Testing GET /files/$FILE_ID/download"
DOWNLOAD_RESPONSE=$(curl -s "${API_ENDPOINT%/files}/files/$FILE_ID/download" \
  -H "Authorization: $TOKEN")

echo "$DOWNLOAD_RESPONSE" | jq .

DOWNLOAD_URL=$(echo "$DOWNLOAD_RESPONSE" | jq -r '.downloadUrl')

if [ "$DOWNLOAD_URL" == "null" ] || [ -z "$DOWNLOAD_URL" ]; then
  handle_error "Failed to get download URL"
fi

# Step 7: Download file
echo -e "\n7. Testing file download using pre-signed URL"
DOWNLOADED_FILE="/tmp/downloaded_test_file.txt"
curl -s "$DOWNLOAD_URL" -o "$DOWNLOADED_FILE"

echo "File downloaded successfully"

# Compare files
if cmp -s "$TEST_FILE" "$DOWNLOADED_FILE"; then
  echo "Downloaded file matches original"
else
  handle_error "Downloaded file does not match original"
fi

# Step 8: Delete file
echo -e "\n8. Testing DELETE /files/$FILE_ID"
DELETE_RESPONSE=$(curl -s -X DELETE "${API_ENDPOINT%/files}/files/$FILE_ID" \
  -H "Authorization: $TOKEN")

echo "$DELETE_RESPONSE" | jq .

# Step 9: List files again (after deletion)
echo -e "\n9. Testing GET /files (after deletion)"
LIST_RESPONSE=$(curl -s "$API_ENDPOINT" -H "Authorization: $TOKEN")
echo "$LIST_RESPONSE" | jq .

FILE_COUNT=$(echo "$LIST_RESPONSE" | jq -r '.metadata.totalFiles // "0"')
echo "Found $FILE_COUNT files after deletion"

# Check if the file is no longer associated with the account
echo -e "\n10. Testing GET /files?accountId=$TEST_ACCOUNT_ID (after deletion)"
ACCOUNT_LIST_RESPONSE=$(curl -s "$API_ENDPOINT?accountId=$TEST_ACCOUNT_ID" -H "Authorization: $TOKEN")
echo "$ACCOUNT_LIST_RESPONSE" | jq .

ACCOUNT_FILE_COUNT=$(echo "$ACCOUNT_LIST_RESPONSE" | jq -r '.metadata.totalFiles // "0"')
ACCOUNT_FILE_COUNT_BEFORE=$(echo "$ACCOUNT_LIST_RESPONSE" | jq -r '.files[] | select(.fileId == "'$FILE_ID'") | .fileId' | wc -l)

if [ "$ACCOUNT_FILE_COUNT_BEFORE" = "0" ]; then
  echo "✅ Successfully verified deleted file is no longer associated with account $TEST_ACCOUNT_ID"
else
  handle_error "Expected file $FILE_ID to be deleted from the account, but it's still associated"
fi

# Clean up
rm -f "$TEST_FILE" "$DOWNLOADED_FILE"

echo -e "\nAll API tests completed successfully! ✅" 