#!/bin/bash
set -e

# Function to handle errors
handle_error() {
  echo "❌ ERROR: $1"
  exit 1
}

# Get bucket name from Terraform output
cd "$(dirname "$0")/../infrastructure/terraform"
S3_BUCKET=$(terraform output -raw file_storage_bucket_name | cat)
cd - > /dev/null

echo "Testing S3 bucket configuration for: $S3_BUCKET"

# Test 1: Verify bucket exists
echo -e "\n1. Testing bucket existence..."
aws s3api get-bucket-location --bucket "$S3_BUCKET" --no-cli-pager || handle_error "Bucket does not exist or is not accessible"
echo "✅ Bucket exists and is accessible"

# Test 2: Verify encryption configuration
echo -e "\n2. Testing encryption configuration..."
ENCRYPTION=$(aws s3api get-bucket-encryption --bucket "$S3_BUCKET" --no-cli-pager 2>/dev/null || echo "NoEncryption")
if [[ "$ENCRYPTION" == *"AES256"* ]]; then
  echo "✅ Bucket has AES256 encryption enabled"
else
  handle_error "Bucket does not have encryption enabled"
fi

# Test 3: Verify CORS configuration
echo -e "\n3. Testing CORS configuration..."
CORS=$(aws s3api get-bucket-cors --bucket "$S3_BUCKET" --no-cli-pager 2>/dev/null || echo "NoCORS")
if [[ "$CORS" == *"localhost"* ]]; then
  echo "✅ CORS allows localhost development"
else
  handle_error "CORS is not properly configured for local development"
fi

# Test 4: Verify lifecycle rules
echo -e "\n4. Testing lifecycle rules..."
LIFECYCLE=$(aws s3api get-bucket-lifecycle-configuration --bucket "$S3_BUCKET" --no-cli-pager 2>/dev/null || echo "NoLifecycle")
if [[ "$LIFECYCLE" == *"Rules"* ]]; then
  echo "✅ Lifecycle rules are configured"
else
  handle_error "Lifecycle rules are not configured"
fi

# Test 5: Verify basic operations (upload, download, delete)
echo -e "\n5. Testing basic operations..."

# Create a temp file for testing
TEST_FILE="/tmp/s3_test_file.txt"
echo "This is a test file for S3 bucket testing" > "$TEST_FILE"
DOWNLOADED_FILE="${TEST_FILE}.downloaded"

echo "   - Uploading test file..."
aws s3 cp "$TEST_FILE" "s3://${S3_BUCKET}/test_file.txt" --no-cli-pager || handle_error "Failed to upload test file"

echo "   - Verifying file exists..."
aws s3 ls "s3://${S3_BUCKET}/test_file.txt" --no-cli-pager || handle_error "Uploaded file not found in bucket"

echo "   - Downloading test file..."
aws s3 cp "s3://${S3_BUCKET}/test_file.txt" "$DOWNLOADED_FILE" --no-cli-pager || handle_error "Failed to download test file"

# Compare files
if cmp -s "$TEST_FILE" "$DOWNLOADED_FILE"; then
  echo "   - Downloaded file matches original"
else
  handle_error "Downloaded file does not match original"
fi

echo "   - Deleting test file..."
aws s3 rm "s3://${S3_BUCKET}/test_file.txt" --no-cli-pager || handle_error "Failed to delete test file"

echo "✅ Basic operations successful"

# Clean up
rm -f "$TEST_FILE" "$DOWNLOADED_FILE"

echo -e "\n✅ All S3 bucket tests passed successfully!"
echo "Bucket is properly configured and operational: $S3_BUCKET"

# Explicitly exit with success
exit 0 