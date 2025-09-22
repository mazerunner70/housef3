#!/bin/bash

# Workflow Diagnostics CLI Wrapper
# Easy-to-use wrapper for the Python workflow diagnostics tool

set -e

# Handle both direct execution and symlink execution
SCRIPT_PATH="${BASH_SOURCE[0]}"
# Resolve symlink to get the actual script location
while [ -L "$SCRIPT_PATH" ]; do
    SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_PATH")" && pwd)"
    SCRIPT_PATH="$(readlink "$SCRIPT_PATH")"
    [[ $SCRIPT_PATH != /* ]] && SCRIPT_PATH="$SCRIPT_DIR/$SCRIPT_PATH"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_PATH")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/workflow_diagnostics.py"

# Environment setup
export PROJECT_NAME=${PROJECT_NAME:-housef3}
export ENVIRONMENT=${ENVIRONMENT:-dev}
export AWS_REGION=${AWS_REGION:-eu-west-2}

# Activate scripts virtual environment if it exists
SCRIPTS_VENV="$(dirname "$SCRIPT_DIR")/venv"
if [ -f "$SCRIPTS_VENV/bin/activate" ]; then
    source "$SCRIPTS_VENV/bin/activate"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Function to print usage
print_usage() {
    echo -e "${BOLD}Workflow Diagnostics CLI${NC}"
    echo "Easy diagnostic tool for tracking workflow operations"
    echo ""
    echo -e "${BOLD}Usage:${NC}"
    echo "  $0 <command> [options]"
    echo ""
    echo -e "${BOLD}Commands:${NC}"
    echo -e "  ${GREEN}status${NC} <operation-id>           Check specific operation status"
    echo -e "  ${GREEN}list${NC} [--status STATUS]          List operations with filters"
    echo -e "  ${GREEN}monitor${NC} [operation-id]          Real-time monitoring"
    echo -e "  ${GREEN}health${NC} [--hours N]              System health analysis"
    echo -e "  ${GREEN}logs${NC} <operation-id>             Show related logs"
    echo -e "  ${GREEN}summary${NC}                         Quick system summary"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  $0 summary                           # Quick overview"
    echo "  $0 health --hours 24                 # 24-hour health report"
    echo "  $0 list --status failed              # List all failed operations"
    echo "  $0 monitor                           # Monitor all active operations"
    echo "  $0 status op_20250120_143022_abc     # Check specific operation"
    echo "  $0 logs op_20250120_143022_abc       # Show logs for operation"
    echo ""
    echo -e "${BOLD}Environment Variables:${NC}"
    echo "  PROJECT_NAME=${PROJECT_NAME}"
    echo "  ENVIRONMENT=${ENVIRONMENT}"
    echo "  AWS_REGION=${AWS_REGION}"
}

# Function to check dependencies
check_dependencies() {
    # Check if Python script exists
    if [ ! -f "$PYTHON_SCRIPT" ]; then
        echo -e "${RED}Error: Python script not found at $PYTHON_SCRIPT${NC}"
        exit 1
    fi
    
    # Check if Python 3 is available
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: python3 is required but not installed${NC}"
        exit 1
    fi
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        echo -e "${YELLOW}Warning: AWS CLI not found. Some features may not work.${NC}"
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        echo -e "${YELLOW}Warning: AWS credentials not configured or invalid.${NC}"
        echo "Please run 'aws configure' or set AWS environment variables."
    fi
}

# Function for quick health check
quick_health() {
    echo -e "${BOLD}🚀 Quick Health Check${NC}"
    echo "========================"
    
    # Check table connectivity
    echo -n "DynamoDB Operations Table: "
    if python3 "$PYTHON_SCRIPT" summary &> /dev/null; then
        echo -e "${GREEN}✓ Connected${NC}"
    else
        echo -e "${RED}✗ Connection failed${NC}"
        return 1
    fi
    
    # Show summary
    python3 "$PYTHON_SCRIPT" summary
}

# Function to show recent failures
show_failures() {
    echo -e "${BOLD}🔥 Recent Failures${NC}"
    echo "=================="
    python3 "$PYTHON_SCRIPT" list --status failed --hours 24 --limit 10
}

# Function to show active operations
show_active() {
    echo -e "${BOLD}⚡ Active Operations${NC}"
    echo "==================="
    
    # Get active operations by filtering multiple statuses
    for status in initiated in_progress waiting_for_approval approved executing; do
        echo -e "\n${BLUE}${status^} Operations:${NC}"
        python3 "$PYTHON_SCRIPT" list --status "$status" --hours 24 --limit 5
    done
}

# Main script logic
main() {
    # Check dependencies first
    check_dependencies
    
    # Handle no arguments
    if [ $# -eq 0 ]; then
        print_usage
        echo ""
        quick_health
        exit 0
    fi
    
    # Handle special commands
    case "$1" in
        "help"|"-h"|"--help")
            print_usage
            exit 0
            ;;
        "check")
            quick_health
            exit $?
            ;;
        "failures")
            show_failures
            exit 0
            ;;
        "active")
            show_active
            exit 0
            ;;
        "watch")
            # Continuous monitoring
            echo -e "${BOLD}🔍 Continuous Monitoring${NC}"
            echo "Press Ctrl+C to stop"
            echo "======================"
            while true; do
                clear
                echo -e "${BOLD}Workflow Status - $(date)${NC}"
                echo "================================"
                python3 "$PYTHON_SCRIPT" summary
                echo ""
                show_active
                sleep 10
            done
            ;;
        *)
            # Pass through to Python script
            python3 "$PYTHON_SCRIPT" "$@"
            ;;
    esac
}

# Run main function with all arguments
main "$@"
