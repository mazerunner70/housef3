#!/bin/bash
set -e

# Function to handle errors and exit with code 1
handle_error() {
  echo "❌ ERROR: $1"
  exit 1
}

# Get DynamoDB table name from Terraform output
cd $(dirname "$0")/../infrastructure/terraform
DYNAMODB_TABLE=$(terraform output -raw dynamodb_table_name)
cd ../..

echo "Testing DynamoDB table configuration for: $DYNAMODB_TABLE"

# Test 1: Verify table exists
echo -e "\n1. Testing table existence..."
TABLE_INFO=$(aws dynamodb describe-table --table-name $DYNAMODB_TABLE 2>/dev/null) || handle_error "Table does not exist or you don't have permission to access it"
echo "✅ Table exists and is accessible"

# Test 2: Verify table schema
echo -e "\n2. Testing table schema..."
# Check key schema for fileId as hash key
FILEID_HASH=$(echo "$TABLE_INFO" | grep -A 5 '"KeySchema"' | grep -A 2 '"AttributeName": "fileId"' | grep -o '"KeyType": "HASH"')
if [ -n "$FILEID_HASH" ]; then
  echo "✅ Table has correct primary key configuration (fileId as HASH key)"
else
  handle_error "Table does not have the correct primary key configuration"
fi

# Check required attributes
FILEATTR=$(echo "$TABLE_INFO" | grep -o '"AttributeName": "fileId"' | wc -l)
USERATTR=$(echo "$TABLE_INFO" | grep -o '"AttributeName": "userId"' | wc -l)
DATEATTR=$(echo "$TABLE_INFO" | grep -o '"AttributeName": "uploadDate"' | wc -l)

if [ "$FILEATTR" -gt 0 ] && [ "$USERATTR" -gt 0 ] && [ "$DATEATTR" -gt 0 ]; then
  echo "✅ Table has all required attributes"
else
  handle_error "Table is missing required attributes"
fi

# Test 3: Verify GSI configuration
echo -e "\n3. Testing Global Secondary Index..."
GSI_COUNT=$(echo "$TABLE_INFO" | grep -o '"IndexName": "UserIndex"' | wc -l)
if [ "$GSI_COUNT" -eq 1 ]; then
  echo "✅ UserIndex GSI is configured"
else
  handle_error "UserIndex GSI is not configured correctly"
fi

# Test 4: Verify point-in-time recovery
echo -e "\n4. Testing point-in-time recovery configuration..."
PITR_INFO=$(aws dynamodb describe-continuous-backups --table-name $DYNAMODB_TABLE)
PITR_STATUS=$(echo "$PITR_INFO" | grep -o '"PointInTimeRecoveryStatus": "ENABLED"')
if [ -n "$PITR_STATUS" ]; then
  echo "✅ Point-in-time recovery is enabled"
else
  handle_error "Point-in-time recovery is not enabled"
fi

# Test 5: Verify encryption
echo -e "\n5. Testing encryption configuration..."
ENCRYPTION=$(echo "$TABLE_INFO" | grep -o '"SSEDescription"')
if [ -n "$ENCRYPTION" ]; then
  echo "✅ Server-side encryption is enabled"
else
  handle_error "Server-side encryption is not enabled"
fi

# Test 6: Test basic CRUD operations
echo -e "\n6. Testing basic CRUD operations..."
TEST_ID="test-$(date +%s)"

# Put item
echo "   - Creating test item..."
aws dynamodb put-item \
  --table-name $DYNAMODB_TABLE \
  --item '{
    "fileId": {"S": "'$TEST_ID'"},
    "userId": {"S": "test-user"},
    "fileName": {"S": "test-file.txt"},
    "uploadDate": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"},
    "fileSize": {"N": "42"},
    "contentType": {"S": "text/plain"}
  }' >/dev/null || handle_error "Failed to create test item"

# Get item
echo "   - Retrieving test item..."
GET_RESULT=$(aws dynamodb get-item \
  --table-name $DYNAMODB_TABLE \
  --key '{"fileId": {"S": "'$TEST_ID'"}}') || handle_error "Failed to retrieve test item"

# Verify item fields
if echo "$GET_RESULT" | grep -q "test-file.txt"; then
  echo "   - Retrieved item matches what was created"
else
  handle_error "Retrieved item does not match what was created"
fi

# Query by GSI
echo "   - Testing query by user ID..."
QUERY_RESULT=$(aws dynamodb query \
  --table-name $DYNAMODB_TABLE \
  --index-name UserIndex \
  --key-condition-expression "userId = :uid" \
  --expression-attribute-values '{":uid": {"S": "test-user"}}') || handle_error "Failed to query by user ID"

# Verify query results
if echo "$QUERY_RESULT" | grep -q "$TEST_ID"; then
  echo "   - Query by user ID returned the test item"
else
  handle_error "Query by user ID did not return the test item"
fi

# Delete item
echo "   - Deleting test item..."
aws dynamodb delete-item \
  --table-name $DYNAMODB_TABLE \
  --key '{"fileId": {"S": "'$TEST_ID'"}}' >/dev/null || handle_error "Failed to delete test item"

# Verify deletion
DELETE_CHECK=$(aws dynamodb get-item \
  --table-name $DYNAMODB_TABLE \
  --key '{"fileId": {"S": "'$TEST_ID'"}}')

if echo "$DELETE_CHECK" | grep -q "Item"; then
  handle_error "Item was not deleted successfully"
else
  echo "   - Item deleted successfully"
fi

echo "✅ CRUD operations successful"

echo -e "\n✅ All DynamoDB table tests passed successfully!"
echo "Table is properly configured and operational: $DYNAMODB_TABLE" 