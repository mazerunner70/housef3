#!/bin/bash
set -e

# Store the original directory
ORIGINAL_DIR=$(pwd)

# Function to handle errors and exit with code 1
handle_error() {
  echo -e "\n❌ ERROR in $1: $2"
  # Return to original directory before exiting
  cd "$ORIGINAL_DIR"
  exit 1
}

# Function to run a test with color-coded output
run_test() {
  TEST_NAME=$1
  TEST_SCRIPT=$2
  
  echo -e "\n\033[1;34m===================================\033[0m"
  echo -e "\033[1;34m Running Test: $TEST_NAME \033[0m"
  echo -e "\033[1;34m===================================\033[0m\n"
  
  # Return to original directory before running each test
  cd "$ORIGINAL_DIR"
  
  # Run the test script
  if bash "$ORIGINAL_DIR/scripts/$TEST_SCRIPT"; then
    echo -e "\n\033[1;32m✅ $TEST_NAME PASSED\033[0m\n"
  else
    echo -e "\n\033[1;31m❌ $TEST_NAME FAILED\033[0m\n"
    handle_error "$TEST_NAME" "Test script returned non-zero exit code"
  fi
}

# Display startup message
echo -e "\n\033[1;33m=========================================\033[0m"
echo -e "\033[1;33m Running All System Tests \033[0m"
echo -e "\033[1;33m=========================================\033[0m\n"

# Run S3 bucket test
run_test "S3 Bucket Configuration" "test_s3_bucket.sh"

# Run DynamoDB test
run_test "DynamoDB Table Configuration" "test_dynamodb.sh"

# Run Authentication test
run_test "Authentication Service" "test_auth.sh"

# Run File Operations test
run_test "File Operations" "test_file_operations.sh"

# Run Account Operations test
run_test "Account Operations" "test_account_operations.sh"

# Run Frontend test
run_test "Frontend Deployment" "test_frontend.sh"

# Final message
echo -e "\n\033[1;32m=========================================\033[0m"
echo -e "\033[1;32m All tests completed successfully! \033[0m"
echo -e "\033[1;32m=========================================\033[0m\n"

# Return to original directory
cd "$ORIGINAL_DIR"
exit 0 