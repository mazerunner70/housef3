#!/bin/bash

# Test script for import operations
# This script tests the import system endpoints

set -e

# Configuration
API_ENDPOINT="${API_ENDPOINT:-https://api.housef3.com}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to make authenticated API calls
make_api_call() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    
    if [ -z "$JWT_TOKEN" ]; then
        print_error "JWT_TOKEN not set. Please set it before running tests."
        exit 1
    fi
    
    if [ -n "$data" ]; then
        curl -s -X "$method" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $JWT_TOKEN" \
            -d "$data" \
            "$API_ENDPOINT$endpoint"
    else
        curl -s -X "$method" \
            -H "Authorization: Bearer $JWT_TOKEN" \
            "$API_ENDPOINT$endpoint"
    fi
}

# Function to check if response is successful
check_response() {
    local response="$1"
    local expected_status="$2"
    
    if echo "$response" | jq -e '.error' > /dev/null 2>&1; then
        print_error "API call failed: $(echo "$response" | jq -r '.error')"
        return 1
    fi
    
    if [ -n "$expected_status" ]; then
        local status=$(echo "$response" | jq -r '.statusCode // .status // "unknown"')
        if [ "$status" != "$expected_status" ]; then
            print_error "Expected status $expected_status, got $status"
            return 1
        fi
    fi
    
    return 0
}

# Test 1: Create Import Job
test_create_import() {
    print_status "Testing create import job..."
    
    local data='{
        "mergeStrategy": "fail_on_conflict",
        "validateOnly": false
    }'
    
    local response=$(make_api_call "POST" "/import" "$data")
    
    if check_response "$response" "uploaded"; then
        print_status "✓ Create import job successful"
        echo "$response" | jq '.'
        
        # Extract import ID for subsequent tests
        IMPORT_ID=$(echo "$response" | jq -r '.importId')
        export IMPORT_ID
        
        return 0
    else
        print_error "✗ Create import job failed"
        return 1
    fi
}

# Test 2: List Import Jobs
test_list_imports() {
    print_status "Testing list import jobs..."
    
    local response=$(make_api_call "GET" "/import")
    
    if check_response "$response"; then
        print_status "✓ List import jobs successful"
        echo "$response" | jq '.'
        return 0
    else
        print_error "✗ List import jobs failed"
        return 1
    fi
}

# Test 3: Get Import Status
test_get_import_status() {
    if [ -z "$IMPORT_ID" ]; then
        print_warning "Skipping get import status test - no import ID available"
        return 0
    fi
    
    print_status "Testing get import status for $IMPORT_ID..."
    
    local response=$(make_api_call "GET" "/import/$IMPORT_ID/status")
    
    if check_response "$response"; then
        print_status "✓ Get import status successful"
        echo "$response" | jq '.'
        return 0
    else
        print_error "✗ Get import status failed"
        return 1
    fi
}

# Test 4: Upload Package (simulated)
test_upload_package() {
    if [ -z "$IMPORT_ID" ]; then
        print_warning "Skipping upload package test - no import ID available"
        return 0
    fi
    
    print_status "Testing upload package for $IMPORT_ID..."
    
    # This is a simplified test - in a real scenario, you'd upload an actual file
    local response=$(make_api_call "POST" "/import/$IMPORT_ID/upload")
    
    if check_response "$response"; then
        print_status "✓ Upload package successful"
        echo "$response" | jq '.'
        return 0
    else
        print_error "✗ Upload package failed"
        return 1
    fi
}

# Test 5: Delete Import Job
test_delete_import() {
    if [ -z "$IMPORT_ID" ]; then
        print_warning "Skipping delete import test - no import ID available"
        return 0
    fi
    
    print_status "Testing delete import job $IMPORT_ID..."
    
    local response=$(make_api_call "DELETE" "/import/$IMPORT_ID")
    
    if check_response "$response"; then
        print_status "✓ Delete import job successful"
        return 0
    else
        print_error "✗ Delete import job failed"
        return 1
    fi
}

# Test 6: Test with invalid import ID
test_invalid_import_id() {
    print_status "Testing with invalid import ID..."
    
    local response=$(make_api_call "GET" "/import/invalid-id/status")
    
    if echo "$response" | jq -e '.error' > /dev/null 2>&1; then
        print_status "✓ Invalid import ID handled correctly"
        return 0
    else
        print_error "✗ Invalid import ID not handled correctly"
        return 1
    fi
}

# Test 7: Test unauthorized access
test_unauthorized_access() {
    print_status "Testing unauthorized access..."
    
    local response=$(curl -s -X "GET" "$API_ENDPOINT/import")
    
    if echo "$response" | jq -e '.error' > /dev/null 2>&1; then
        print_status "✓ Unauthorized access blocked correctly"
        return 0
    else
        print_error "✗ Unauthorized access not blocked correctly"
        return 1
    fi
}

# Main test execution
main() {
    print_status "Starting import operations tests..."
    print_status "API Endpoint: $API_ENDPOINT"
    print_status "Environment: $ENVIRONMENT"
    
    local tests_passed=0
    local tests_failed=0
    
    # Run tests
    if test_create_import; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    if test_list_imports; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    if test_get_import_status; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    if test_upload_package; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    if test_delete_import; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    if test_invalid_import_id; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    if test_unauthorized_access; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    # Print summary
    echo
    print_status "Test Summary:"
    print_status "Tests passed: $tests_passed"
    if [ $tests_failed -gt 0 ]; then
        print_error "Tests failed: $tests_failed"
    else
        print_status "Tests failed: $tests_failed"
    fi
    
    if [ $tests_failed -eq 0 ]; then
        print_status "All tests passed! ✓"
        exit 0
    else
        print_error "Some tests failed! ✗"
        exit 1
    fi
}

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    print_error "jq is required but not installed. Please install jq to run these tests."
    exit 1
fi

# Check if JWT_TOKEN is set
if [ -z "$JWT_TOKEN" ]; then
    print_warning "JWT_TOKEN not set. Some tests will be skipped."
    print_warning "To run all tests, set JWT_TOKEN environment variable."
fi

# Run main function
main "$@" 