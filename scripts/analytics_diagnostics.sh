#!/bin/bash

# Analytics Diagnostics Script
# Usage: ./scripts/analytics_diagnostics.sh [command] [environment]

set -e

ENVIRONMENT=${2:-dev}
FUNCTION_NAME="housef3-${ENVIRONMENT}-analytics-processor"
LOG_GROUP="/aws/lambda/${FUNCTION_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_usage() {
    echo "Analytics Diagnostics Script"
    echo ""
    echo "Usage: $0 [command] [environment]"
    echo ""
    echo "Commands:"
    echo "  status      - Check current processing status"
    echo "  disable     - Disable automatic processing"
    echo "  enable      - Enable automatic processing"
    echo "  run         - Manually run analytics processing"
    echo "  logs        - View recent logs"
    echo "  watch       - Watch logs in real-time"
    echo "  pending     - Check pending analytics (requires AWS profile setup)"
    echo ""
    echo "Environment: dev (default), staging, prod"
    echo ""
    echo "Examples:"
    echo "  $0 status dev"
    echo "  $0 disable"
    echo "  $0 run"
    echo "  $0 logs"
}

check_rule_status() {
    echo -e "${BLUE}Checking CloudWatch Events rule status...${NC}"
    RULE_NAME="housef3-${ENVIRONMENT}-analytics-processor-schedule"
    
    STATUS=$(aws events describe-rule --name "$RULE_NAME" --query 'State' --output text 2>/dev/null || echo "NOT_FOUND")
    
    if [ "$STATUS" = "NOT_FOUND" ]; then
        echo -e "${RED}❌ Rule not found: $RULE_NAME${NC}"
        return 1
    elif [ "$STATUS" = "ENABLED" ]; then
        echo -e "${GREEN}✅ Automatic processing is ENABLED${NC}"
        echo -e "${YELLOW}📅 Running every 10 minutes${NC}"
    elif [ "$STATUS" = "DISABLED" ]; then
        echo -e "${YELLOW}⏸️  Automatic processing is DISABLED${NC}"
        echo -e "${BLUE}💡 Use '$0 enable' to re-enable${NC}"
    else
        echo -e "${RED}❓ Unknown status: $STATUS${NC}"
    fi
}

disable_processing() {
    echo -e "${YELLOW}Disabling automatic analytics processing...${NC}"
    RULE_NAME="housef3-${ENVIRONMENT}-analytics-processor-schedule"
    
    aws events disable-rule --name "$RULE_NAME"
    echo -e "${GREEN}✅ Automatic processing disabled${NC}"
    echo -e "${BLUE}💡 Use '$0 enable' to re-enable when ready${NC}"
}

enable_processing() {
    echo -e "${GREEN}Enabling automatic analytics processing...${NC}"
    RULE_NAME="housef3-${ENVIRONMENT}-analytics-processor-schedule"
    
    aws events enable-rule --name "$RULE_NAME"
    echo -e "${GREEN}✅ Automatic processing enabled${NC}"
    echo -e "${BLUE}📅 Will run every 10 minutes${NC}"
}

run_manual_processing() {
    echo -e "${BLUE}Manually invoking analytics processor...${NC}"
    
    # Create diagnostic event
    DIAGNOSTIC_EVENT=$(cat << EOF
{
  "source": "manual-diagnostic",
  "detail-type": "Manual Analytics Processing",
  "detail": {
    "diagnostic_mode": true,
    "requested_by": "$(whoami)",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "environment": "$ENVIRONMENT"
  }
}
EOF
)
    
    echo -e "${YELLOW}📤 Sending invocation request...${NC}"
    
    # Invoke the function
    aws lambda invoke \
        --function-name "$FUNCTION_NAME" \
        --payload "$DIAGNOSTIC_EVENT" \
        --cli-binary-format raw-in-base64-out \
        response.json > /dev/null
    
    echo -e "${GREEN}✅ Analytics processor invoked${NC}"
    
    # Show response
    echo -e "${BLUE}📋 Response:${NC}"
    cat response.json | jq '.' 2>/dev/null || cat response.json
    rm -f response.json
    
    echo ""
    echo -e "${YELLOW}📊 Viewing recent logs (last 5 minutes)...${NC}"
    sleep 2
    aws logs tail "$LOG_GROUP" --since 5m 2>/dev/null || echo "No recent logs found"
}

view_logs() {
    echo -e "${BLUE}📊 Viewing recent analytics processor logs...${NC}"
    aws logs tail "$LOG_GROUP" --since 30m 2>/dev/null || echo "No recent logs found"
}

watch_logs() {
    echo -e "${BLUE}👀 Watching analytics processor logs in real-time...${NC}"
    echo -e "${YELLOW}💡 Press Ctrl+C to stop watching${NC}"
    echo ""
    aws logs tail "$LOG_GROUP" --follow 2>/dev/null || echo "Failed to tail logs"
}

check_pending() {
    echo -e "${BLUE}🔍 This would check pending analytics in DynamoDB...${NC}"
    echo -e "${YELLOW}💡 Requires direct DynamoDB access setup${NC}"
    echo ""
    echo "To check manually:"
    echo "1. Go to AWS Console → DynamoDB → Tables"
    echo "2. Find: housef3-${ENVIRONMENT}-analytics-status"
    echo "3. Scan for items where computationNeeded = true"
}

# Main script logic
case "${1:-}" in
    "status")
        check_rule_status
        ;;
    "disable")
        disable_processing
        ;;
    "enable")
        enable_processing
        ;;
    "run")
        run_manual_processing
        ;;
    "logs")
        view_logs
        ;;
    "watch")
        watch_logs
        ;;
    "pending")
        check_pending
        ;;
    *)
        print_usage
        exit 1
        ;;
esac 