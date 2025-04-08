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

# 3b. Test account ownership validation with a made-up account ID
echo -e "\n3b. Testing POST /accounts/invalid-account-id/files (ownership validation)"
INVALID_ID="invalid-account-$(date +%s)"
INVALID_UPLOAD_ENDPOINT="$API_ENDPOINT/$INVALID_ID/files"
echo "Invalid upload endpoint: $INVALID_UPLOAD_ENDPOINT"

INVALID_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: $ID_TOKEN" \
    -d "$UPLOAD_PAYLOAD" \
    "$INVALID_UPLOAD_ENDPOINT")

echo "Response from invalid account ID:"
echo "$INVALID_RESPONSE" | jq .

ERROR_MSG=$(echo "$INVALID_RESPONSE" | jq -r '.message')
if [[ "$ERROR_MSG" == *"not found"* ]]; then
    echo "✅ Successfully verified account existence validation"
else
    echo "⚠️ WARNING: Expected 'not found' error but got a different response"
fi

# 3c. Test regular file upload with account association via the /files/upload endpoint
echo -e "\n3c. Testing POST /files/upload with valid account association"
FILES_UPLOAD_ENDPOINT="${API_ENDPOINT%accounts}files/upload"
ASSOCIATION_PAYLOAD="{\"fileName\":\"association_test.txt\", \"contentType\":\"text/plain\", \"fileSize\": $FILE_SIZE, \"accountId\": \"$ACCOUNT_ID\"}"
echo "Files upload endpoint: $FILES_UPLOAD_ENDPOINT"
echo "Association payload: $ASSOCIATION_PAYLOAD"

ASSOCIATION_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: $ID_TOKEN" \
    -d "$ASSOCIATION_PAYLOAD" \
    "$FILES_UPLOAD_ENDPOINT")

echo "Association response:"
echo "$ASSOCIATION_RESPONSE" | jq .

ASSOCIATION_FILE_ID=$(echo "$ASSOCIATION_RESPONSE" | jq -r '.fileId')
ASSOCIATION_UPLOAD_URL=$(echo "$ASSOCIATION_RESPONSE" | jq -r '.uploadUrl')
RETURNED_ACCOUNT_ID=$(echo "$ASSOCIATION_RESPONSE" | jq -r '.accountId')

if [ -z "$ASSOCIATION_FILE_ID" ] || [ "$ASSOCIATION_FILE_ID" = "null" ]; then
    echo "Error: Failed to get association file ID from response"
    exit 1
fi

if [ "$RETURNED_ACCOUNT_ID" = "$ACCOUNT_ID" ]; then
    echo "✅ Account ID returned in response matches the requested account ID"
else
    echo "❌ Account ID mismatch: requested $ACCOUNT_ID but got $RETURNED_ACCOUNT_ID"
    exit 1
fi

echo "Received association file ID: $ASSOCIATION_FILE_ID"

# 3d. Upload file to S3 using pre-signed URL from association test
echo -e "\n3d. Testing file upload using association pre-signed URL"
ASSOCIATION_RESULT=$(curl -s -X PUT -H "Content-Type: text/plain" --upload-file "$TEST_FILE" "$ASSOCIATION_UPLOAD_URL")
echo "Association file uploaded successfully"

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

# Check if the file count decreased by 1 after deletion
EXPECTED_COUNT=$((FILE_COUNT - 1))
if [ "$FINAL_FILE_COUNT" -eq "$EXPECTED_COUNT" ]; then
    echo "✅ File successfully deleted from account (count decreased from $FILE_COUNT to $FINAL_FILE_COUNT)"
else
    echo "❌ File was not successfully deleted from account (expected $EXPECTED_COUNT files, found $FINAL_FILE_COUNT)"
    exit 1
fi

# 9. Test account deletion with associated files
echo -e "\n9. Testing account deletion with associated files"
echo "api endpoint: ${API_ENDPOINT}"
# Create a new account for deletion testing
echo "Creating a test account for deletion test..."
ACCOUNT_CREATE_RESPONSE=$(curl -s -X POST \
  -H "Authorization: $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"accountName\":\"Test Account For Deletion $(date +%s)\", \"accountType\":\"savings\", \"institution\":\"Test Deletion Bank\", \"balance\":500, \"currency\":\"USD\", \"notes\":\"Test account for deletion test\"}" \
  "$API_ENDPOINT")

echo "Account creation response:"
echo "$ACCOUNT_CREATE_RESPONSE" | jq .

DELETION_ACCOUNT_ID=$(echo "$ACCOUNT_CREATE_RESPONSE" | jq -r '.account.accountId')
if [ -z "$DELETION_ACCOUNT_ID" ] || [ "$DELETION_ACCOUNT_ID" == "null" ]; then
  echo "❌ Failed to create test account for deletion"
  exit 1
fi

echo "Created test account with ID: $DELETION_ACCOUNT_ID"

# Associate a file with the account
echo "Associating test file with account for deletion test..."
ASSOC_UPLOAD_RESPONSE=$(curl -s -X POST \
  -H "Authorization: $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"fileName\":\"deletion_test.txt\", \"contentType\":\"text/plain\", \"fileSize\": 52}" \
  "$API_ENDPOINT/$DELETION_ACCOUNT_ID/files")

echo "Association upload response:"
echo "$ASSOC_UPLOAD_RESPONSE" | jq .

ASSOC_FILE_ID=$(echo "$ASSOC_UPLOAD_RESPONSE" | jq -r '.fileId')
ASSOC_UPLOAD_URL=$(echo "$ASSOC_UPLOAD_RESPONSE" | jq -r '.uploadUrl')

if [ -z "$ASSOC_FILE_ID" ] || [ "$ASSOC_FILE_ID" == "null" ]; then
  echo "❌ Failed to get file upload URL for deletion test"
  exit 1
fi

# Upload file content
echo "Uploading file content..."
curl -s -X PUT -T "/tmp/account_test_file.txt" \
  -H "Content-Type: text/plain" \
  "$ASSOC_UPLOAD_URL" > /dev/null

echo "File successfully associated with account for deletion test"

# Verify the file is associated with the account
ACCOUNT_FILES_BEFORE=$(curl -s -H "Authorization: $ID_TOKEN" "$API_ENDPOINT/$DELETION_ACCOUNT_ID/files")
FILE_COUNT_BEFORE=$(echo "$ACCOUNT_FILES_BEFORE" | jq -r '.metadata.totalFiles // 0')
echo "Account has $FILE_COUNT_BEFORE associated files before deletion"

if [ "$FILE_COUNT_BEFORE" -lt 1 ]; then
  echo "❌ File was not properly associated with account for deletion test"
  exit 1
fi

# Delete the account
echo "Deleting account $DELETION_ACCOUNT_ID with associated files..."
ACCOUNT_DELETE_RESPONSE=$(curl -s -X DELETE -H "Authorization: $ID_TOKEN" "$API_ENDPOINT/$DELETION_ACCOUNT_ID")
echo "$ACCOUNT_DELETE_RESPONSE" | jq .

# Verify the account is deleted
ACCOUNT_CHECK=$(curl -s -H "Authorization: $ID_TOKEN" "$API_ENDPOINT/$DELETION_ACCOUNT_ID")
ACCOUNT_STATUS=$(echo "$ACCOUNT_CHECK" | jq -r '.message')

if [[ "$ACCOUNT_STATUS" != *"not found"* ]]; then
  echo "❌ Account was not properly deleted"
  exit 1
fi

echo "✅ Account was successfully deleted"

# Check if the file still exists but is not associated with the account
FILE_CHECK=$(curl -s -H "Authorization: $ID_TOKEN" "${API_ENDPOINT%accounts}files/$ASSOC_FILE_ID")
echo "File check after account deletion:"
echo "$FILE_CHECK" | jq .

# Determine if file exists
FILE_EXISTS=$(echo "$FILE_CHECK" | jq -r 'if has("message") and .message | contains("not found") then "no" else "yes" end')
if [ "$FILE_EXISTS" == "no" ]; then
  echo "❌ File should still exist after account deletion"
  exit 1
fi

# Check if account association was removed
FILE_ACCOUNT_ID=$(echo "$FILE_CHECK" | jq -r '.accountId // "null"')
echo "File's account ID after account deletion: $FILE_ACCOUNT_ID"

if [ "$FILE_ACCOUNT_ID" == "$DELETION_ACCOUNT_ID" ]; then
  echo "❌ File is still associated with the deleted account"
  exit 1
else
  echo "✅ File association was properly removed when account was deleted"
fi

echo -e "\nAll account-file association tests completed successfully! ✅" 