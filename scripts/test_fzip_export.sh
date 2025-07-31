#!/bin/bash

# FZIP Export End-to-End Test Script
# This script tests the complete FZIP export functionality in the deployed environment

set -e

# Configuration
ENVIRONMENT=${1:-dev}
API_BASE_URL=""
USER_TOKEN=""
EXPORT_ID=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if environment variables are set
check_environment() {
    log_info "Checking environment configuration..."
    
    if [ -z "$API_BASE_URL" ]; then
        if [ "$ENVIRONMENT" = "dev" ]; then
            API_BASE_URL="https://api-dev.housef3.com"
        elif [ "$ENVIRONMENT" = "prod" ]; then
            API_BASE_URL="https://api.housef3.com"
        else
            log_error "Unknown environment: $ENVIRONMENT"
            exit 1
        fi
    fi
    
    log_info "Using API base URL: $API_BASE_URL"
    
    if [ -z "$USER_TOKEN" ]; then
        log_error "USER_TOKEN environment variable must be set"
        log_info "Please export USER_TOKEN=your_jwt_token"
        exit 1
    fi
    
    log_info "Environment configuration validated"
}

# Test API connectivity
test_api_connectivity() {
    log_info "Testing API connectivity..."
    
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $USER_TOKEN" \
        "$API_BASE_URL/accounts")
    
    if [ "$response" = "200" ]; then
        log_info "API connectivity test passed"
    else
        log_error "API connectivity test failed (HTTP $response)"
        exit 1
    fi
}

# Initiate FZIP export
initiate_export() {
    log_info "Initiating FZIP export..."
    
    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Authorization: Bearer $USER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "exportType": "complete",
            "includeAnalytics": false,
            "description": "End-to-end test export"
        }' \
        "$API_BASE_URL/export")
    
    # Split response body and status code
    response_body=$(echo "$response" | head -n -1)
    status_code=$(echo "$response" | tail -n 1)
    
    if [ "$status_code" = "201" ]; then
        EXPORT_ID=$(echo "$response_body" | grep -o '"exportId":"[^"]*"' | cut -d'"' -f4)
        log_info "Export initiated successfully. Export ID: $EXPORT_ID"
    else
        log_error "Failed to initiate export (HTTP $status_code)"
        echo "Response: $response_body"
        exit 1
    fi
}

# Wait for export completion
wait_for_export_completion() {
    log_info "Waiting for export completion (Export ID: $EXPORT_ID)..."
    
    max_attempts=30
    attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        attempt=$((attempt + 1))
        
        response=$(curl -s -w "\n%{http_code}" \
            -H "Authorization: Bearer $USER_TOKEN" \
            "$API_BASE_URL/export/$EXPORT_ID/status")
        
        response_body=$(echo "$response" | head -n -1)
        status_code=$(echo "$response" | tail -n 1)
        
        if [ "$status_code" = "200" ]; then
            export_status=$(echo "$response_body" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
            progress=$(echo "$response_body" | grep -o '"progress":[0-9]*' | cut -d':' -f2)
            
            log_info "Export status: $export_status, Progress: ${progress}%"
            
            case "$export_status" in
                "export_completed")
                    log_info "Export completed successfully!"
                    return 0
                    ;;
                "export_failed")
                    log_error "Export failed"
                    echo "Response: $response_body"
                    exit 1
                    ;;
                *)
                    log_info "Export in progress... (attempt $attempt/$max_attempts)"
                    sleep 10
                    ;;
            esac
        else
            log_error "Failed to get export status (HTTP $status_code)"
            exit 1
        fi
    done
    
    log_error "Export did not complete within expected time"
    exit 1
}

# Test download URL generation
test_download_url() {
    log_info "Testing download URL generation..."
    
    response=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer $USER_TOKEN" \
        "$API_BASE_URL/export/$EXPORT_ID/download")
    
    response_body=$(echo "$response" | head -n -1)
    status_code=$(echo "$response" | tail -n 1)
    
    if [ "$status_code" = "302" ] || [ "$status_code" = "200" ]; then
        log_info "Download URL generation test passed"
        
        # Extract download URL from response
        download_url=$(echo "$response_body" | grep -o '"downloadUrl":"[^"]*"' | cut -d'"' -f4)
        if [ -n "$download_url" ]; then
            log_info "Download URL: $download_url"
        fi
    else
        log_error "Download URL generation test failed (HTTP $status_code)"
        echo "Response: $response_body"
        exit 1
    fi
}

# Validate FZIP package structure
validate_fzip_package() {
    log_info "Validating FZIP package structure..."
    
    # Get download URL
    response=$(curl -s \
        -H "Authorization: Bearer $USER_TOKEN" \
        "$API_BASE_URL/export/$EXPORT_ID/status")
    
    download_url=$(echo "$response" | grep -o '"downloadUrl":"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$download_url" ]; then
        log_error "No download URL found in export status"
        exit 1
    fi
    
    # Download the FZIP package
    temp_file=$(mktemp)
    curl -s -L -o "$temp_file" "$download_url"
    
    if [ ! -f "$temp_file" ] || [ ! -s "$temp_file" ]; then
        log_error "Failed to download FZIP package"
        rm -f "$temp_file"
        exit 1
    fi
    
    log_info "FZIP package downloaded successfully"
    
    # Validate ZIP structure
    if command -v unzip >/dev/null 2>&1; then
        log_info "Validating ZIP file structure..."
        
        # Check if it's a valid ZIP file
        if unzip -t "$temp_file" >/dev/null 2>&1; then
            log_info "ZIP file structure is valid"
            
            # List contents
            log_info "FZIP package contents:"
            unzip -l "$temp_file" | head -20
            
            # Check for required files
            required_files=("manifest.json" "data/accounts.json" "data/transactions.json" "data/categories.json")
            
            for file in "${required_files[@]}"; do
                if unzip -l "$temp_file" | grep -q "$file"; then
                    log_info "✓ Required file found: $file"
                else
                    log_warn "⚠ Required file missing: $file"
                fi
            done
            
        else
            log_error "Invalid ZIP file structure"
            rm -f "$temp_file"
            exit 1
        fi
    else
        log_warn "unzip not available, skipping ZIP structure validation"
    fi
    
    # Clean up
    rm -f "$temp_file"
    log_info "FZIP package validation completed"
}

# Test export history listing
test_export_history() {
    log_info "Testing export history listing..."
    
    response=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer $USER_TOKEN" \
        "$API_BASE_URL/export?limit=10")
    
    response_body=$(echo "$response" | head -n -1)
    status_code=$(echo "$response" | tail -n 1)
    
    if [ "$status_code" = "200" ]; then
        export_count=$(echo "$response_body" | grep -o '"total":[0-9]*' | cut -d':' -f2)
        log_info "Export history test passed. Total exports: $export_count"
        
        # Check if our export is in the list
        if echo "$response_body" | grep -q "$EXPORT_ID"; then
            log_info "✓ Current export found in history"
        else
            log_warn "⚠ Current export not found in history"
        fi
    else
        log_error "Export history test failed (HTTP $status_code)"
        echo "Response: $response_body"
        exit 1
    fi
}

# Clean up test export
cleanup_test_export() {
    log_info "Cleaning up test export..."
    
    response=$(curl -s -w "\n%{http_code}" \
        -X DELETE \
        -H "Authorization: Bearer $USER_TOKEN" \
        "$API_BASE_URL/export/$EXPORT_ID")
    
    status_code=$(echo "$response" | tail -n 1)
    
    if [ "$status_code" = "200" ] || [ "$status_code" = "204" ]; then
        log_info "Test export cleaned up successfully"
    else
        log_warn "Failed to clean up test export (HTTP $status_code)"
    fi
}

# Main test execution
main() {
    log_info "Starting FZIP Export End-to-End Test"
    log_info "Environment: $ENVIRONMENT"
    
    check_environment
    test_api_connectivity
    initiate_export
    wait_for_export_completion
    test_download_url
    validate_fzip_package
    test_export_history
    cleanup_test_export
    
    log_info "🎉 All FZIP export tests passed successfully!"
}

# Help function
show_help() {
    echo "FZIP Export End-to-End Test Script"
    echo ""
    echo "Usage: $0 [environment]"
    echo ""
    echo "Arguments:"
    echo "  environment    Target environment (dev|prod) [default: dev]"
    echo ""
    echo "Environment Variables:"
    echo "  USER_TOKEN     JWT token for authentication (required)"
    echo "  API_BASE_URL   Override default API base URL (optional)"
    echo ""
    echo "Examples:"
    echo "  export USER_TOKEN=your_jwt_token"
    echo "  $0 dev"
    echo "  $0 prod"
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    *)
        main
        ;;
esac