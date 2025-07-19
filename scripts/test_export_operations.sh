#!/bin/bash

# Test script for export operations
# This script tests the export operations functionality

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_ENDPOINT="${API_ENDPOINT:-http://localhost:3000}"
USER_TOKEN="${USER_TOKEN:-}"

echo -e "${YELLOW}Testing Export Operations${NC}"
echo "API Endpoint: $API_ENDPOINT"
echo ""

# Function to make API calls
make_api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    
    if [ -n "$data" ]; then
        curl -s -X "$method" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $USER_TOKEN" \
            -d "$data" \
            "$API_ENDPOINT$endpoint"
    else
        curl -s -X "$method" \
            -H "Authorization: Bearer $USER_TOKEN" \
            "$API_ENDPOINT$endpoint"
    fi
}

# Test 1: List exports (should return empty list initially)
echo -e "${YELLOW}Test 1: List exports${NC}"
response=$(make_api_call "GET" "/export")
echo "Response: $response"
echo ""

# Test 2: Initiate export
echo -e "${YELLOW}Test 2: Initiate export${NC}"
export_data='{
    "exportType": "complete",
    "includeAnalytics": false,
    "description": "Test export"
}'
response=$(make_api_call "POST" "/export" "$export_data")
echo "Response: $response"

# Extract export ID from response
export_id=$(echo "$response" | jq -r '.exportId // empty')
if [ -n "$export_id" ] && [ "$export_id" != "null" ]; then
    echo -e "${GREEN}✓ Export initiated successfully. Export ID: $export_id${NC}"
else
    echo -e "${RED}✗ Failed to initiate export${NC}"
    exit 1
fi
echo ""

# Test 3: Get export status
echo -e "${YELLOW}Test 3: Get export status${NC}"
response=$(make_api_call "GET" "/export/$export_id/status")
echo "Response: $response"
echo ""

# Test 4: List exports again (should now show the export)
echo -e "${YELLOW}Test 4: List exports (should show the export)${NC}"
response=$(make_api_call "GET" "/export")
echo "Response: $response"
echo ""

# Test 5: Get export download URL (if completed)
echo -e "${YELLOW}Test 5: Get export download URL${NC}"
response=$(make_api_call "GET" "/export/$export_id/download")
echo "Response: $response"
echo ""

# Test 6: Delete export
echo -e "${YELLOW}Test 6: Delete export${NC}"
response=$(make_api_call "DELETE" "/export/$export_id")
echo "Response: $response"
echo ""

# Test 7: Verify export is deleted
echo -e "${YELLOW}Test 7: Verify export is deleted${NC}"
response=$(make_api_call "GET" "/export")
echo "Response: $response"
echo ""

echo -e "${GREEN}Export operations test completed!${NC}" 