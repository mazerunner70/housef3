#!/bin/bash
set -e

# Store the original directory
ORIGINAL_DIR=$(pwd)

# Determine if we're in the scripts directory or not
if [[ "$ORIGINAL_DIR" != *"/scripts" ]]; then
  # If we're not in the scripts directory, navigate to it
  cd "$ORIGINAL_DIR/scripts" || exit 1
  SCRIPTS_DIR=$(pwd)
else
  # We're already in the scripts directory
  SCRIPTS_DIR="$ORIGINAL_DIR"
fi

# Function to handle errors and exit with code 1
handle_error() {
  echo -e "\n❌ ERROR in $1: $2"
  # Return to original directory before exiting
  cd "$ORIGINAL_DIR"
  exit 1
}

# Function to run a test with color-coded output and timeout
run_test() {
  TEST_NAME=$1
  TEST_SCRIPT=$2
  TIMEOUT=300  # 5 minutes timeout
  
  echo -e "\n\033[1;34m===================================\033[0m"
  echo -e "\033[1;34m Running Test: $TEST_NAME \033[0m"
  echo -e "\033[1;34m===================================\033[0m\n"
  
  # Export non-interactive mode flag for tests
  export NONINTERACTIVE=true
  export AWS_PAGER=""
  
  # Run the test script with timeout
  if timeout $TIMEOUT bash "./$TEST_SCRIPT"; then
    echo -e "\n\033[1;32m✅ $TEST_NAME PASSED\033[0m\n"
  else
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
      echo -e "\n\033[1;31m❌ $TEST_NAME TIMED OUT\033[0m\n"
      handle_error "$TEST_NAME" "Test timed out after $TIMEOUT seconds"
    else
      echo -e "\n\033[1;31m❌ $TEST_NAME FAILED\033[0m\n"
      handle_error "$TEST_NAME" "Test script returned non-zero exit code: $EXIT_CODE"
    fi
  fi
}

# Display startup message
echo -e "\n\033[1;33m=========================================\033[0m"
echo -e "\033[1;33m Running All System Tests \033[0m"
echo -e "\033[1;33m=========================================\033[0m\n"

# Individual test execution commands with improved error checking
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

# Run Account-File Association test
run_test "Account-File Association" "test_account_files.sh"

# Run Frontend test
run_test "Frontend Deployment" "test_frontend.sh"

# Final message
echo -e "\n\033[1;32m=========================================\033[0m"
echo -e "\033[1;32m All tests completed successfully! \033[0m"
echo -e "\033[1;32m=========================================\033[0m\n"

# Return to original directory
cd "$ORIGINAL_DIR"
exit 0 