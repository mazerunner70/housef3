#!/bin/bash

# Trigger Analytics Refresh via API
# This script uses the analytics refresh API endpoint to trigger analytics processing.

set -e  # Exit on any error

# Configuration
API_ENDPOINT="${VITE_API_ENDPOINT:-https://dev-api.housef3.com}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output  
RED='\033[0;31m'
GREEN='\033[0;32m' 
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}${BOLD}"
    echo "================================================"
    echo "  Analytics API Refresh Tool"
    echo "================================================"
    echo -e "${NC}"
    echo -e "API Endpoint: ${BOLD}$API_ENDPOINT${NC}"
    echo ""
}

print_usage() {
    echo -e "${BOLD}Usage:${NC}"
    echo "  $0 [OPTIONS]"
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo "  --token TOKEN         Your authentication token (required)"
    echo "  --all-types           Refresh all analytic types (default)"
    echo "  --types TYPE1,TYPE2   Refresh specific analytic types"
    echo "  --force               Force refresh even if data is current"
    echo "  --check-status        Check current analytics status only"
    echo "  --help                Show this help message"
    echo ""
    echo -e "${BOLD}Analytic Types:${NC}"
    echo "  cash_flow, financial_health, category_trends, account_efficiency"
    echo "  merchant_analysis, payment_patterns, spending_behavior"
    echo "  budget_performance, debt_management, credit_health"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  $0 --token your_jwt_token --check-status"
    echo "  $0 --token your_jwt_token --all-types"
    echo "  $0 --token your_jwt_token --types cash_flow,financial_health"
    echo "  $0 --token your_jwt_token --force"
    echo ""
    echo -e "${BOLD}Getting Your Token:${NC}"
    echo "  1. Log into the web app and open browser developer tools"
    echo "  2. Go to Application/Storage tab → Local Storage"
    echo "  3. Copy the 'auth_token' value"
}

check_requirements() {
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}❌ curl is required but not installed${NC}"
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        echo -e "${YELLOW}⚠️  jq not found - JSON responses will not be formatted${NC}"
    fi
}

format_json() {
    if command -v jq &> /dev/null; then
        jq '.'
    else
        cat
    fi
}

check_analytics_status() {
    local token="$1"
    
    echo -e "${BLUE}🔍 Checking analytics status...${NC}"
    
    local response=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        "$API_ENDPOINT/analytics/status")
    
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n -1)
    
    if [[ "$http_code" == "200" ]]; then
        echo -e "${GREEN}✅ Analytics status retrieved successfully:${NC}"
        echo "$body" | format_json
    else
        echo -e "${RED}❌ Failed to get analytics status (HTTP $http_code):${NC}"
        echo "$body" | format_json
        return 1
    fi
}

refresh_analytics() {
    local token="$1"
    local analytic_types="$2"
    local force="$3"
    
    echo -e "${GREEN}🔄 Triggering analytics refresh...${NC}"
    
    # Build request body safely without sed manipulation
    local request_body=""
    local force_value="false"
    if [[ "$force" == "true" ]]; then
        force_value="true"
    fi
    
    if [[ -n "$analytic_types" ]]; then
        # Convert comma-separated types to JSON array using safe string construction
        local types_json=""
        IFS=',' read -ra TYPE_ARRAY <<< "$analytic_types"
        for i in "${!TYPE_ARRAY[@]}"; do
            if [[ $i -gt 0 ]]; then
                types_json+=","
            fi
            # Escape quotes and backslashes in the type name
            local escaped_type="${TYPE_ARRAY[i]//\\/\\\\}"  # Escape backslashes first
            escaped_type="${escaped_type//\"/\\\"}"         # Then escape quotes
            types_json+="\"$escaped_type\""
        done
        request_body="{\"force\": $force_value, \"analytic_types\": [$types_json]}"
    else
        request_body="{\"force\": $force_value}"
    fi
    
    echo -e "${BLUE}📤 Request body: $request_body${NC}"
    
    local response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "$request_body" \
        "$API_ENDPOINT/analytics/refresh")
    
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n -1)
    
    if [[ "$http_code" == "200" ]]; then
        echo -e "${GREEN}✅ Analytics refresh triggered successfully:${NC}"
        echo "$body" | format_json
        
        echo ""
        echo -e "${BLUE}📊 Analytics will be processed in the background.${NC}"
        echo -e "${BLUE}Check status with: $0 --token $token --check-status${NC}"
        echo -e "${BLUE}Or monitor logs with: ./scripts/analytics_diagnostics.sh logs${NC}"
    else
        echo -e "${RED}❌ Failed to trigger analytics refresh (HTTP $http_code):${NC}"
        echo "$body" | format_json
        return 1
    fi
}

main() {
    print_header
    check_requirements

    local token=""
    local analytic_types=""
    local force="false"
    local check_status_only="false"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --token)
                token="$2"
                shift 2
                ;;
            --all-types)
                analytic_types=""  # Empty means all types
                shift
                ;;
            --types)
                analytic_types="$2"
                shift 2
                ;;
            --force)
                force="true"
                shift
                ;;
            --check-status)
                check_status_only="true"
                shift
                ;;
            --help)
                print_usage
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Unknown option: $1${NC}"
                print_usage
                exit 1
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "$token" ]]; then
        echo -e "${RED}❌ Authentication token is required${NC}"
        echo ""
        print_usage
        exit 1
    fi

    # Execute requested action
    if [[ "$check_status_only" == "true" ]]; then
        check_analytics_status "$token"
    else
        # Always check status first
        if check_analytics_status "$token"; then
            echo ""
            refresh_analytics "$token" "$analytic_types" "$force"
        fi
    fi
}

main "$@" 