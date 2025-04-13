#!/bin/bash
set -e

# Store original directory
ORIGINAL_DIR=$(pwd)
SCRIPTS_DIR="$ORIGINAL_DIR"

# Check if we're in the /scripts directory, otherwise navigate to it
if [[ "$ORIGINAL_DIR" != *"/scripts" ]]; then
    cd "$(dirname "$0")"
    SCRIPTS_DIR=$(pwd)
    echo "Changed to scripts directory: $SCRIPTS_DIR"
fi

# Error handling
handle_error() {
    echo "❌ ERROR: $1"
    cd "$ORIGINAL_DIR"
    exit 1
}

# Function to run tests with timeout
run_test() {
    local test_script="$1"
    local timeout_seconds=300  # 5 minutes timeout
    
    echo -e "\n==================================================================="
    echo "🚀 Running test: $test_script"
    echo "==================================================================="
    
    # Run the test with timeout
    timeout $timeout_seconds bash "$test_script"
    local exit_code=$?
    
    # Check exit status
    if [ $exit_code -eq 124 ]; then
        handle_error "Test $test_script timed out after $timeout_seconds seconds"
    elif [ $exit_code -ne 0 ]; then
        handle_error "Test $test_script failed with exit code $exit_code"
    else
        echo -e "\n✅ Test $test_script completed successfully"
    fi
}

# Startup message
echo "🔍 Starting comprehensive test suite for housef3 project"
echo "📂 Running from directory: $SCRIPTS_DIR"
echo "⏱️  $(date)"
echo "==================================================================="

# S3 Bucket tests
echo -e "\n📦 Step 1: Testing S3 bucket configuration"
run_test "./test_s3_bucket.sh"

# DynamoDB tests
echo -e "\n🗄️ Step 2: Testing DynamoDB table configuration"
run_test "./test_dynamodb.sh"

# Authentication tests
echo -e "\n🔐 Step 3: Testing authentication services"
run_test "./test_auth.sh"

# Account operations tests
echo -e "\n📊 Step 4: Testing account operations API"
run_test "./test_account_operations.sh"

# File operations tests
echo -e "\n📄 Step 5: Testing file operations API"
run_test "./test_file_operations.sh"

# Account-file association tests
echo -e "\n🔗 Step 6: Testing account-file association functionality"
run_test "./test_account_files.sh"

# Transaction parsing tests
echo -e "\n📊 Step 7: Testing transaction file parsing"
run_test "./test_transaction_parsing.sh"

# Return to original directory
cd "$ORIGINAL_DIR"

# Final success message
echo -e "\n==================================================================="
echo "🎉 All tests completed successfully!"
echo "✅ S3 bucket configuration verified"
echo "✅ DynamoDB tables configuration verified"
echo "✅ Authentication services operational"
echo "✅ Account operations API functioning"
echo "✅ File operations API functioning"
echo "✅ Account-file associations verified"
echo "✅ Transaction file parsing verified"
echo "==================================================================="
echo "⏱️  Tests completed at $(date)" 