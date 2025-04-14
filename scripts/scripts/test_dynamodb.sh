#!/bin/bash
set -e

# Function to handle errors and exit with code 1
handle_error() {
  echo "❌ ERROR: $1"
  exit 1
}

# Get table names from Terraform output
cd $(dirname "$0")/../infrastructure/terraform
ACCOUNTS_TABLE=$(terraform output -raw accounts_table_name | cat)
TRANSACTION_FILES_TABLE=$(terraform output -raw transaction_files_table_name | cat)
cd ../..

echo "Testing DynamoDB tables configuration"
echo "Accounts table: $ACCOUNTS_TABLE"
echo "Transaction files table: $TRANSACTION_FILES_TABLE"

# Test 1: Verify tables exist
echo -e "\n1. Testing tables existence..."

# Check accounts table
ACCOUNTS_DESC=$(aws dynamodb describe-table --table-name $ACCOUNTS_TABLE --no-cli-pager 2>/dev/null) || handle_error "Accounts table does not exist"
echo "✅ Accounts table exists"

# Check transaction files table
FILES_DESC=$(aws dynamodb describe-table --table-name $TRANSACTION_FILES_TABLE --no-cli-pager 2>/dev/null) || handle_error "Transaction files table does not exist"
echo "✅ Transaction files table exists"

# Test 2: Verify accounts table schema
echo -e "\n2. Testing accounts table schema..."

# Check accounts table primary key
if [[ "$ACCOUNTS_DESC" == *"accountId"* ]]; then
  echo "✅ Accounts table has correct primary key (accountId)"
else
  handle_error "Accounts table has incorrect primary key"
fi

# Check accounts table GSI for userId
if [[ "$ACCOUNTS_DESC" == *"userId"* ]] && [[ "$ACCOUNTS_DESC" == *"IndexName"* ]]; then
  echo "✅ Accounts table has GSI with userId"
else
  handle_error "Accounts table is missing required GSI with userId"
fi

# Test 3: Verify transaction files table schema
echo -e "\n3. Testing transaction files table schema..."

# Check transaction files table primary key
if [[ "$FILES_DESC" == *"fileId"* ]]; then
  echo "✅ Transaction files table has correct primary key (fileId)"
else
  handle_error "Transaction files table has incorrect primary key"
fi

# Check transaction files table GSI for userId
if [[ "$FILES_DESC" == *"userId"* ]] && [[ "$FILES_DESC" == *"IndexName"* ]]; then
  echo "✅ Transaction files table has GSI with userId"
else
  handle_error "Transaction files table is missing required GSI with userId"
fi

# Check transaction files table GSI for accountId if exists
if [[ "$FILES_DESC" == *"accountId"* ]] && [[ "$FILES_DESC" == *"IndexName"* ]]; then
  echo "✅ Transaction files table has account-file association GSI with accountId"
else
  echo "⚠️  NOTE: Transaction files table does not have an accountId GSI. This is recommended for account-file associations."
fi

# Test 4: Test basic operations with a test account
echo -e "\n4. Testing basic operations on accounts table..."

# Generate a unique test ID
TEST_ID=$(date +%s)
TEST_ACCOUNT_ID="test-account-$TEST_ID"
TEST_USER_ID="test-user-$TEST_ID"

# Create a test account
echo "   - Creating test account..."
aws dynamodb put-item \
  --table-name $ACCOUNTS_TABLE \
  --item "{
    \"accountId\": {\"S\": \"$TEST_ACCOUNT_ID\"},
    \"userId\": {\"S\": \"$TEST_USER_ID\"},
    \"accountName\": {\"S\": \"Test Account\"},
    \"accountType\": {\"S\": \"checking\"},
    \"balance\": {\"S\": \"1000.00\"},
    \"createdAt\": {\"S\": \"$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)\"}
  }" --no-cli-pager 2>/dev/null || handle_error "Failed to create test account"

# Get the test account
echo "   - Retrieving test account..."
GET_RESULT=$(aws dynamodb get-item \
  --table-name $ACCOUNTS_TABLE \
  --key "{\"accountId\": {\"S\": \"$TEST_ACCOUNT_ID\"}}" --no-cli-pager 2>/dev/null) || handle_error "Failed to retrieve test account"

if [[ "$GET_RESULT" == *"$TEST_ACCOUNT_ID"* ]]; then
  echo "   - Account retrieved successfully"
else
  handle_error "Retrieved account data does not match"
fi

# Get the index name for userId
USER_ID_INDEX=$(echo "$ACCOUNTS_DESC" | grep -o '"IndexName": "[^"]*"' | grep -o '"[^"]*"$' | tr -d '"' | head -1)

# Query the test account by userId
echo "   - Querying test account by userId using index $USER_ID_INDEX..."
QUERY_RESULT=$(aws dynamodb query \
  --table-name $ACCOUNTS_TABLE \
  --index-name "$USER_ID_INDEX" \
  --key-condition-expression "userId = :uid" \
  --expression-attribute-values "{\":uid\": {\"S\": \"$TEST_USER_ID\"}}" --no-cli-pager 2>/dev/null) || handle_error "Failed to query account by userId"

if [[ "$QUERY_RESULT" == *"$TEST_ACCOUNT_ID"* ]]; then
  echo "   - Account queried by userId successfully"
else
  handle_error "GSI query results do not match expected data"
fi

# Delete the test account
echo "   - Deleting test account..."
aws dynamodb delete-item \
  --table-name $ACCOUNTS_TABLE \
  --key "{\"accountId\": {\"S\": \"$TEST_ACCOUNT_ID\"}}" --no-cli-pager 2>/dev/null || handle_error "Failed to delete test account"

echo "✅ Basic operations on accounts table successful"

# Test 5: Test basic operations with a test file record
echo -e "\n5. Testing basic operations on transaction files table..."

# Generate a unique test ID
TEST_FILE_ID="test-file-$TEST_ID"

# Create a test file record
echo "   - Creating test file record..."
aws dynamodb put-item \
  --table-name $TRANSACTION_FILES_TABLE \
  --item "{
    \"fileId\": {\"S\": \"$TEST_FILE_ID\"},
    \"userId\": {\"S\": \"$TEST_USER_ID\"},
    \"fileName\": {\"S\": \"test-file.csv\"},
    \"uploadDate\": {\"S\": \"$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)\"},
    \"fileSize\": {\"S\": \"1024\"},
    \"fileFormat\": {\"S\": \"csv\"},
    \"s3Key\": {\"S\": \"test-key\"},
    \"processingStatus\": {\"S\": \"pending\"}
  }" --no-cli-pager 2>/dev/null || handle_error "Failed to create test file record"

# Get the test file record
echo "   - Retrieving test file record..."
GET_RESULT=$(aws dynamodb get-item \
  --table-name $TRANSACTION_FILES_TABLE \
  --key "{\"fileId\": {\"S\": \"$TEST_FILE_ID\"}}" --no-cli-pager 2>/dev/null) || handle_error "Failed to retrieve test file record"

if [[ "$GET_RESULT" == *"$TEST_FILE_ID"* ]]; then
  echo "   - File record retrieved successfully"
else
  handle_error "Retrieved file record data does not match"
fi

# Get the index name for userId in files table
FILES_USER_ID_INDEX=$(echo "$FILES_DESC" | grep -o '"IndexName": "[^"]*"' | grep -o '"[^"]*"$' | tr -d '"' | head -1)

# Query the test file by userId
echo "   - Querying test file by userId using index $FILES_USER_ID_INDEX..."
QUERY_RESULT=$(aws dynamodb query \
  --table-name $TRANSACTION_FILES_TABLE \
  --index-name "$FILES_USER_ID_INDEX" \
  --key-condition-expression "userId = :uid" \
  --expression-attribute-values "{\":uid\": {\"S\": \"$TEST_USER_ID\"}}" --no-cli-pager 2>/dev/null) || handle_error "Failed to query file by userId"

if [[ "$QUERY_RESULT" == *"$TEST_FILE_ID"* ]]; then
  echo "   - File queried by userId successfully"
else
  handle_error "GSI query results do not match expected data"
fi

# Delete the test file record
echo "   - Deleting test file record..."
aws dynamodb delete-item \
  --table-name $TRANSACTION_FILES_TABLE \
  --key "{\"fileId\": {\"S\": \"$TEST_FILE_ID\"}}" --no-cli-pager 2>/dev/null || handle_error "Failed to delete test file record"

echo "✅ Basic operations on transaction files table successful"

echo -e "\n✅ All DynamoDB tests passed successfully!"
echo "Tables are properly configured and operational" 