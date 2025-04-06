#!/bin/bash
set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CONFIG_FILE="$SCRIPT_DIR/config.json"

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed. Please install jq first."
    exit 1
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found at $CONFIG_FILE"
    exit 1
fi

# Get the values from terraform output
cd ../infrastructure/terraform
API_ENDPOINT=$(terraform output -raw api_accounts_endpoint)
STORAGE_BUCKET=$(terraform output -raw file_storage_bucket_name)
CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)

# Read username and password from config
USERNAME=$(jq -r '.username' "$CONFIG_FILE")
PASSWORD=$(jq -r '.password' "$CONFIG_FILE")

echo "API Endpoint: $API_ENDPOINT"
echo "Storage Bucket: $STORAGE_BUCKET"
echo "Client ID: $CLIENT_ID"
echo "User Pool ID: $USER_POOL_ID"
echo "Username: $USERNAME"

# Get token from Cognito
echo "Getting authentication token..."
AUTH_RESULT=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters USERNAME=$USERNAME,PASSWORD=$PASSWORD)

ID_TOKEN=$(echo $AUTH_RESULT | jq -r '.AuthenticationResult.IdToken')
echo "Token received, first 20 chars: ${ID_TOKEN:0:20}..."

# Create a test file
TEST_FILE="/tmp/account_test_file.txt"
echo "This is a test file for account association testing" > "$TEST_FILE"
FILE_SIZE=$(wc -c < "$TEST_FILE")
echo "Created test file: $TEST_FILE (size: $FILE_SIZE bytes)"

# 1. Get list of accounts to select one
echo -e "\n1. Testing GET /accounts (listing accounts)"
ACCOUNT_LIST_RESPONSE=$(curl -s -H "Authorization: $ID_TOKEN" "$API_ENDPOINT")
echo "$ACCOUNT_LIST_RESPONSE" | jq .

# Extract the first account ID
ACCOUNT_ID=$(echo "$ACCOUNT_LIST_RESPONSE" | jq -r '.accounts[0].accountId')
ACCOUNT_NAME=$(echo "$ACCOUNT_LIST_RESPONSE" | jq -r '.accounts[0].accountName')

if [ -z "$ACCOUNT_ID" ] || [ "$ACCOUNT_ID" = "null" ]; then
    echo "Error: No accounts found. Please create an account first."
    exit 1
fi

echo "Using account ID: $ACCOUNT_ID"
echo "Account name: $ACCOUNT_NAME"

# 2. List files for the selected account (should be empty initially)
echo -e "\n2. Testing GET /accounts/$ACCOUNT_ID/files (initial list)"
INITIAL_FILES_RESPONSE=$(curl -s -H "Authorization: $ID_TOKEN" "$API_ENDPOINT/$ACCOUNT_ID/files")
echo "$INITIAL_FILES_RESPONSE" | jq .

INITIAL_FILE_COUNT=$(echo "$INITIAL_FILES_RESPONSE" | jq -r '.metadata.totalFiles')
echo "Account has $INITIAL_FILE_COUNT files initially"

# 3. Upload a file to the account
echo -e "\n3. Testing POST /accounts/$ACCOUNT_ID/files (upload)"
UPLOAD_ENDPOINT="$API_ENDPOINT/$ACCOUNT_ID/files"
UPLOAD_PAYLOAD="{\"fileName\":\"account_test_file.txt\", \"contentType\":\"text/plain\", \"fileSize\": $FILE_SIZE}"
echo "Upload endpoint: $UPLOAD_ENDPOINT"
echo "Upload payload: $UPLOAD_PAYLOAD"
echo "Authorization header: Authorization: ${ID_TOKEN:0:20}..."

UPLOAD_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: $ID_TOKEN" \
    -d "$UPLOAD_PAYLOAD" \
    "$UPLOAD_ENDPOINT")

echo "Upload response:"
echo "$UPLOAD_RESPONSE" | jq .

FILE_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.fileId')
UPLOAD_URL=$(echo "$UPLOAD_RESPONSE" | jq -r '.uploadUrl')

if [ -z "$FILE_ID" ] || [ "$FILE_ID" = "null" ]; then
    echo "Error: Failed to get file ID from response"
    exit 1
fi

echo "Received file ID: $FILE_ID"

# 4. Upload file to S3 using pre-signed URL
echo -e "\n4. Testing file upload using pre-signed URL"
UPLOAD_RESULT=$(curl -s -X PUT -H "Content-Type: text/plain" --upload-file "$TEST_FILE" "$UPLOAD_URL")
echo "File uploaded successfully"

# 5. List files for the account again (should include the new file)
echo -e "\n5. Testing GET /accounts/$ACCOUNT_ID/files (after upload)"
FILES_RESPONSE=$(curl -s -H "Authorization: $ID_TOKEN" "$API_ENDPOINT/$ACCOUNT_ID/files")
echo "$FILES_RESPONSE" | jq .

FILE_COUNT=$(echo "$FILES_RESPONSE" | jq -r '.metadata.totalFiles')
echo "Account has $FILE_COUNT files after upload"

# Verify file is associated with the account
FILE_IN_ACCOUNT=$(echo "$FILES_RESPONSE" | jq -r --arg fileId "$FILE_ID" '.files[] | select(.fileId == $fileId) | .fileId')
if [ "$FILE_IN_ACCOUNT" = "$FILE_ID" ]; then
    echo "✅ File is correctly associated with the account"
else
    echo "❌ File is not associated with the account"
    exit 1
fi

# 6. List files normally to verify the file is also in the main list
echo -e "\n6. Testing GET /files (checking main file list)"
MAIN_FILES_RESPONSE=$(curl -s -H "Authorization: $ID_TOKEN" "${API_ENDPOINT%accounts}files")
echo "$MAIN_FILES_RESPONSE" | jq .

# Verify file appears in the main list
FILE_IN_MAIN_LIST=$(echo "$MAIN_FILES_RESPONSE" | jq -r --arg fileId "$FILE_ID" '.files[] | select(.fileId == $fileId) | .fileId')
if [ "$FILE_IN_MAIN_LIST" = "$FILE_ID" ]; then
    echo "✅ File also appears in the main files list"
else
    echo "❌ File is not found in the main files list"
    exit 1
fi

# 7. Delete the test file
echo -e "\n7. Testing DELETE /files/$FILE_ID"
DELETE_RESPONSE=$(curl -s -X DELETE -H "Authorization: $ID_TOKEN" "${API_ENDPOINT%accounts}files/$FILE_ID")
echo "$DELETE_RESPONSE" | jq .

# 8. Verify file is removed from account files
echo -e "\n8. Testing GET /accounts/$ACCOUNT_ID/files (after deletion)"
FINAL_FILES_RESPONSE=$(curl -s -H "Authorization: $ID_TOKEN" "$API_ENDPOINT/$ACCOUNT_ID/files")
echo "$FINAL_FILES_RESPONSE" | jq .

FINAL_FILE_COUNT=$(echo "$FINAL_FILES_RESPONSE" | jq -r '.metadata.totalFiles')
echo "Account has $FINAL_FILE_COUNT files after deletion"

if [ "$FINAL_FILE_COUNT" = "0" ] || [ "$INITIAL_FILE_COUNT" = "$FINAL_FILE_COUNT" ]; then
    echo "✅ File successfully deleted from account"
else
    echo "❌ File was not successfully deleted from account"
    exit 1
fi

echo -e "\nAll account-file association tests completed successfully! ✅" 