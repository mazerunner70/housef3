#!/bin/bash
set -e

# Function to handle errors and exit with code 1
handle_error() {
  echo "❌ ERROR: $1"
  exit 1
}

# Get S3 bucket name from Terraform output
cd $(dirname "$0")/../infrastructure/terraform
S3_BUCKET=$(terraform output -raw file_storage_bucket_name)
cd ../..

echo "Testing S3 bucket configuration for: $S3_BUCKET"

# Test 1: Verify bucket exists
echo -e "\n1. Testing bucket existence..."
aws s3api head-bucket --bucket $S3_BUCKET || handle_error "Bucket does not exist or you don't have permission to access it"
echo "✅ Bucket exists and is accessible"

# Test 2: Verify encryption configuration
echo -e "\n2. Testing encryption configuration..."
ENCRYPTION=$(aws s3api get-bucket-encryption --bucket $S3_BUCKET)
if [[ "$ENCRYPTION" == *"AES256"* ]]; then
  echo "✅ Bucket has AES256 encryption enabled"
else
  handle_error "Bucket encryption is not configured correctly"
fi

# Test 3: Verify CORS configuration
echo -e "\n3. Testing CORS configuration..."
CORS=$(aws s3api get-bucket-cors --bucket $S3_BUCKET)
if [[ -z "$CORS" ]]; then
  handle_error "CORS configuration is missing"
fi
if [[ "$CORS" == *"localhost:5173"* ]]; then
  echo "✅ CORS allows localhost development"
else
  handle_error "CORS is not configured for localhost development"
fi

# Test 4: Verify lifecycle rules
echo -e "\n4. Testing lifecycle rules..."
LIFECYCLE=$(aws s3api get-bucket-lifecycle-configuration --bucket $S3_BUCKET)
if [[ -z "$LIFECYCLE" ]]; then
  handle_error "Lifecycle configuration is missing"
fi
if [[ "$LIFECYCLE" == *"STANDARD_IA"* ]]; then
  echo "✅ Lifecycle rules are configured"
else
  handle_error "Lifecycle rules are not configured correctly"
fi

# Test 5: Test basic operations with a test file
echo -e "\n5. Testing basic operations..."
TEST_FILE="/tmp/s3_test_file.txt"
TEST_KEY="test_file.txt"

# Create a test file
echo "This is a test file for S3 bucket testing" > $TEST_FILE

# Upload the file
echo "   - Uploading test file..."
aws s3 cp $TEST_FILE s3://$S3_BUCKET/$TEST_KEY || handle_error "Failed to upload test file"

# Check if the file exists
echo "   - Verifying file exists..."
aws s3 ls s3://$S3_BUCKET/$TEST_KEY || handle_error "Uploaded file not found"

# Download the file
echo "   - Downloading test file..."
aws s3 cp s3://$S3_BUCKET/$TEST_KEY ${TEST_FILE}.downloaded || handle_error "Failed to download test file"

# Compare the files
if cmp -s "$TEST_FILE" "${TEST_FILE}.downloaded"; then
  echo "   - Downloaded file matches original"
else
  handle_error "Downloaded file does not match original"
fi

# Delete the file
echo "   - Deleting test file..."
aws s3 rm s3://$S3_BUCKET/$TEST_KEY || handle_error "Failed to delete test file"

# Clean up local test files
rm -f $TEST_FILE ${TEST_FILE}.downloaded

echo "✅ Basic operations successful"

echo -e "\n✅ All S3 bucket tests passed successfully!"
echo "Bucket is properly configured and operational: $S3_BUCKET" 