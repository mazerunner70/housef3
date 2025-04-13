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
CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
FILE_STORAGE_BUCKET=$(terraform output -raw file_storage_bucket_name)
cd - > /dev/null

# Load username and password from config.json
CONFIG_FILE="$(dirname "$0")/config.json"
USERNAME=$(jq -r '.username' "$CONFIG_FILE")
PASSWORD=$(jq -r '.password' "$CONFIG_FILE")

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

# Create test files directory
TEST_FILES_DIR="/tmp/test_transaction_files"
mkdir -p "$TEST_FILES_DIR"

# Create sample OFX file
echo "Creating sample OFX file..."
cat > "$TEST_FILES_DIR/test.ofx" << 'EOF'
OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
  <SIGNONMSGSRSV1>
    <SONRS>
      <STATUS>
        <CODE>0</CODE>
        <SEVERITY>INFO</SEVERITY>
      </STATUS>
      <DTSERVER>20240101120000</DTSERVER>
      <LANGUAGE>ENG</LANGUAGE>
    </SONRS>
  </SIGNONMSGSRSV1>
  <BANKMSGSRSV1>
    <STMTTRNRS>
      <TRNUID>1</TRNUID>
      <STATUS>
        <CODE>0</CODE>
        <SEVERITY>INFO</SEVERITY>
      </STATUS>
      <STMTRS>
        <CURDEF>USD</CURDEF>
        <BANKACCTFROM>
          <BANKID>123456789</BANKID>
          <ACCTID>12345678901234</ACCTID>
          <ACCTTYPE>CHECKING</ACCTTYPE>
        </BANKACCTFROM>
        <BANKTRANLIST>
          <DTSTART>20240101</DTSTART>
          <DTEND>20240131</DTEND>
          <STMTTRN>
            <TRNTYPE>DEBIT</TRNTYPE>
            <DTPOSTED>20240101</DTPOSTED>
            <TRNAMT>-50.00</TRNAMT>
            <FITID>20240101001</FITID>
            <NAME>Test Transaction 1</NAME>
            <MEMO>Test Memo 1</MEMO>
          </STMTTRN>
          <STMTTRN>
            <TRNTYPE>CREDIT</TRNTYPE>
            <DTPOSTED>20240102</DTPOSTED>
            <TRNAMT>100.00</TRNAMT>
            <FITID>20240102001</FITID>
            <NAME>Test Transaction 2</NAME>
            <MEMO>Test Memo 2</MEMO>
          </STMTTRN>
        </BANKTRANLIST>
        <LEDGERBAL>
          <BALAMT>1000.00</BALAMT>
          <DTASOF>20240131</DTASOF>
        </LEDGERBAL>
      </STMTRS>
    </STMTTRNRS>
  </BANKMSGSRSV1>
</OFX>
EOF

# Create sample CSV file
echo "Creating sample CSV file..."
cat > "$TEST_FILES_DIR/test.csv" << 'EOF'
Date,Description,Amount,Balance,Type,Category
2024-01-01,Opening Balance,1000.00,1000.00,CREDIT,Initial Balance
2024-01-02,Test Transaction 1,-50.00,950.00,DEBIT,Shopping
2024-01-03,Test Transaction 2,100.00,1050.00,CREDIT,Income
EOF

# Function to test file upload and processing
test_file_upload() {
  local file_path="$1"
  local file_format="$2"
  local content_type="$3"
  
  echo -e "\nTesting $file_format file processing..."
  
  # Get file size
  local file_size=$(stat -c%s "$file_path")
  
  # Get upload URL
  echo "Getting upload URL... $API_ENDPOINT/upload"
  local upload_response=$(curl -s -X POST "$API_ENDPOINT/upload" \
    -H "Authorization: $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"fileName\":\"$(basename "$file_path")\", \"contentType\":\"$content_type\", \"fileSize\": $file_size, \"fileFormat\": \"$file_format\"}")
  
  echo "Upload response:"
  echo "$upload_response" | jq .
  
  local file_id=$(echo "$upload_response" | jq -r '.fileId')
  local upload_url=$(echo "$upload_response" | jq -r '.uploadUrl')
  
  if [ "$file_id" == "null" ] || [ -z "$file_id" ]; then
    handle_error "Failed to get file ID for $file_format file"
  fi
  
  # Upload file
  echo "Uploading file..."
  curl -s -X PUT "$upload_url" \
    -H "Content-Type: $content_type" \
    --data-binary @"$file_path"
  
  echo "Getting processing status check API endpoint: $API_ENDPOINT/$file_id"
  # Wait for processing
  echo "Waiting for file processing..."
  local max_attempts=5
  local attempt=1
  local processing_complete=false
  
  while [ $attempt -le $max_attempts ]; do
    local status_response=$(curl -s "$API_ENDPOINT/$file_id" \
      -H "Authorization: $TOKEN")
    echo "Status response:"
    echo "$status_response" | jq .
    
    local processing_status=$(echo "$status_response" | jq -r '.processingStatus')
    echo "Processing status: $processing_status (attempt $attempt/$max_attempts)"
    
    if [ "$processing_status" = "processed" ]; then
      processing_complete=true
      break
    elif [ "$processing_status" = "error" ]; then
      handle_error "File processing failed for $file_format file"
    fi
    
    sleep 2
    ((attempt++))
  done
  
  if [ "$processing_complete" = false ]; then
    handle_error "Timeout waiting for $file_format file processing"
  fi
  
  # Verify transactions
  echo "Verifying transactions..."
  local file_details=$(curl -s "$API_ENDPOINT/$file_id" \
    -H "Authorization: $TOKEN")
  
  echo "File details:"
  echo "$file_details" | jq .
  
  local record_count=$(echo "$file_details" | jq -r '.recordCount // 0')
  if [ "$record_count" -eq 0 ]; then
    handle_error "No transactions found in processed $file_format file"
  fi
  
  echo "✅ Successfully processed $file_format file with $record_count transactions"
}

# Test OFX file
test_file_upload "$TEST_FILES_DIR/test.ofx" "ofx" "application/x-ofx"

# Test CSV file
test_file_upload "$TEST_FILES_DIR/test.csv" "csv" "text/csv"

# Clean up
echo -e "\nCleaning up test files..."
rm -rf "$TEST_FILES_DIR"

echo -e "\n✅ All transaction parsing tests completed successfully!" 