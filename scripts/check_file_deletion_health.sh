#!/bin/bash

# File Deletion System Health Check Script
# Usage: ./check_file_deletion_health.sh [coordination-id]

set -e

ENVIRONMENT=${ENVIRONMENT:-dev}
COORD_ID=$1
TIME_WINDOW=${TIME_WINDOW:-"30 minutes ago"}

echo "🔍 File Deletion System Health Check"
echo "Environment: $ENVIRONMENT"
echo "Time Window: $TIME_WINDOW"
if [ -n "$COORD_ID" ]; then
    echo "Coordination ID: $COORD_ID"
fi
echo "=================================="

# Function to check log group
check_logs() {
    local log_group=$1
    local description=$2
    local filter_pattern=$3
    
    echo ""
    echo "📋 $description"
    echo "Log Group: $log_group"
    
    if ! aws logs describe-log-groups --log-group-name-prefix "$log_group" --query 'logGroups[0].logGroupName' --output text 2>/dev/null | grep -q "$log_group"; then
        echo "❌ Log group not found - Lambda may not be deployed"
        return
    fi
    
    local start_time=$(date -d "$TIME_WINDOW" +%s)000
    local events
    
    if [ -n "$COORD_ID" ]; then
        # Use quotes around coordination ID for better matching
        events=$(aws logs filter-log-events \
            --log-group-name "$log_group" \
            --filter-pattern "\"$COORD_ID\"" \
            --start-time "$start_time" \
            --query 'events[*].[eventTime,message]' \
            --output text 2>/dev/null || echo "")
    else
        events=$(aws logs filter-log-events \
            --log-group-name "$log_group" \
            --filter-pattern "$filter_pattern" \
            --start-time "$start_time" \
            --query 'events[*].[eventTime,message]' \
            --output text 2>/dev/null || echo "")
    fi
    
    if [ -z "$events" ]; then
        echo "ℹ️  No events found"
    else
        echo "✅ Events found:"
        echo "$events" | head -5
        local count=$(echo "$events" | wc -l)
        if [ "$count" -gt 5 ]; then
            echo "... and $((count - 5)) more events"
        fi
    fi
}

# Check each component
check_logs "/aws/lambda/housef3-$ENVIRONMENT-file-operations" "File Operations Handler" "FileDeleteRequestedEvent"
check_logs "/aws/lambda/housef3-$ENVIRONMENT-file-deletion-consumer" "File Deletion Consumer" "coordination"
check_logs "/aws/lambda/housef3-$ENVIRONMENT-analytics-consumer" "Analytics Consumer" "file.delete_requested"
check_logs "/aws/lambda/housef3-$ENVIRONMENT-categorization-consumer" "Categorization Consumer" "file.delete_requested"

echo ""
echo "🔧 EventBridge Health"
echo "====================="

# Check EventBridge rules
echo "📡 Checking EventBridge rules..."
aws events list-rules --name-prefix "housef3-$ENVIRONMENT" --query 'Rules[?contains(Name, `deletion`)].{Name:Name,State:State}' --output table

echo ""
echo "📊 Recent EventBridge Metrics"
echo "============================="

# Get EventBridge metrics for the last hour
aws cloudwatch get-metric-statistics \
    --namespace AWS/Events \
    --metric-name SuccessfulInvocations \
    --dimensions Name=RuleName,Value="housef3-$ENVIRONMENT-file-deletion-events" \
    --start-time $(date -d '1 hour ago' --iso-8601) \
    --end-time $(date --iso-8601) \
    --period 3600 \
    --statistics Sum \
    --query 'Datapoints[0].Sum' \
    --output text 2>/dev/null | \
    { read sum; echo "File deletion events in last hour: ${sum:-0}"; }

echo ""
echo "🎯 Quick Troubleshooting Tips"
echo "============================="
echo "1. If no events found: Check if ENABLE_EVENT_PUBLISHING=true"
echo "2. If coordination timeouts: Check consumer Lambda errors"
echo "3. If events not routing: Verify EventBridge rules are enabled"
echo "4. For detailed tracing: Use coordination ID with this script"
echo ""
echo "Example usage with coordination ID:"
echo "  $0 12345678-1234-1234-1234-123456789abc"
