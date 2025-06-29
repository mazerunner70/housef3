#!/bin/bash

# Trigger Analytics for Existing Data
# This script helps trigger analytics processing for existing transaction files and accounts.

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/trigger_analytics_for_existing_data.py"

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
    echo "  Trigger Analytics for Existing Data"
    echo "================================================"
    echo -e "${NC}"
}

print_usage() {
    echo -e "${BOLD}Usage:${NC}"
    echo "  $0 [COMMAND] [OPTIONS]"
    echo ""
    echo -e "${BOLD}Commands:${NC}"
    echo "  check          Check which users need analytics processing"
    echo "  trigger-all    Trigger analytics for all users with transaction data"
    echo "  trigger-user   Trigger analytics for a specific user"
    echo "  force-all      Force analytics refresh for all users"
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo "  --user-id ID   Specific user ID (for trigger-user command)"
    echo "  --dry-run      Show what would be done without making changes"
    echo "  --help         Show this help message"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  $0 check                                    # Check who needs processing"
    echo "  $0 trigger-all --dry-run                    # See what would be done"
    echo "  $0 trigger-all                              # Actually trigger for all users"
    echo "  $0 trigger-user --user-id abc123            # Trigger for specific user"
    echo "  $0 force-all --dry-run                      # Force refresh for everyone"
}

check_requirements() {
    # Check if Python script exists
    if [[ ! -f "$PYTHON_SCRIPT" ]]; then
        echo -e "${RED}❌ Python script not found: $PYTHON_SCRIPT${NC}"
        exit 1
    fi

    # Check if we're in a virtual environment or have required packages
    if ! python3 -c "import boto3" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Warning: boto3 not found. You may need to activate your virtual environment:${NC}"
        echo "   cd $PROJECT_ROOT/backend && source venv/bin/activate"
        echo ""
    fi
}

check_analytics_status() {
    echo -e "${BLUE}🔍 Checking analytics status...${NC}"
    cd "$PROJECT_ROOT"
    python3 "$PYTHON_SCRIPT" --dry-run
}

trigger_all_users() {
    local dry_run_flag=""
    if [[ "$1" == "--dry-run" ]]; then
        dry_run_flag="--dry-run"
    fi

    echo -e "${GREEN}🚀 Triggering analytics for all users with transaction data...${NC}"
    cd "$PROJECT_ROOT"
    python3 "$PYTHON_SCRIPT" $dry_run_flag
}

trigger_specific_user() {
    local user_id="$1"
    local dry_run_flag=""
    if [[ "$2" == "--dry-run" ]]; then
        dry_run_flag="--dry-run"
    fi

    if [[ -z "$user_id" ]]; then
        echo -e "${RED}❌ User ID required for trigger-user command${NC}"
        echo "Usage: $0 trigger-user --user-id YOUR_USER_ID"
        exit 1
    fi

    echo -e "${GREEN}🎯 Triggering analytics for user: $user_id${NC}"
    cd "$PROJECT_ROOT"
    python3 "$PYTHON_SCRIPT" --user-id "$user_id" $dry_run_flag
}

force_all_users() {
    local dry_run_flag=""
    if [[ "$1" == "--dry-run" ]]; then
        dry_run_flag="--dry-run"
    fi

    echo -e "${YELLOW}⚡ Force refreshing analytics for ALL users...${NC}"
    cd "$PROJECT_ROOT"
    python3 "$PYTHON_SCRIPT" --force $dry_run_flag
}

monitor_progress() {
    echo -e "${BLUE}📊 To monitor analytics processing progress, use:${NC}"
    echo "  ./scripts/analytics_diagnostics.sh logs"
    echo ""
    echo -e "${BLUE}📈 To check analytics status:${NC}"
    echo "  ./scripts/analytics_diagnostics.sh status"
}

main() {
    print_header
    check_requirements

    local command="$1"
    shift || true

    case "$command" in
        "check")
            check_analytics_status
            ;;
        "trigger-all")
            trigger_all_users "$@"
            if [[ "$*" != *"--dry-run"* ]]; then
                echo ""
                monitor_progress
            fi
            ;;
        "trigger-user")
            local user_id=""
            local dry_run=""
            
            while [[ $# -gt 0 ]]; do
                case $1 in
                    --user-id)
                        user_id="$2"
                        shift 2
                        ;;
                    --dry-run)
                        dry_run="--dry-run"
                        shift
                        ;;
                    *)
                        echo -e "${RED}❌ Unknown option: $1${NC}"
                        print_usage
                        exit 1
                        ;;
                esac
            done
            
            trigger_specific_user "$user_id" "$dry_run"
            if [[ -z "$dry_run" ]]; then
                echo ""
                monitor_progress
            fi
            ;;
        "force-all")
            force_all_users "$@"
            if [[ "$*" != *"--dry-run"* ]]; then
                echo ""
                monitor_progress
            fi
            ;;
        "--help"|"help"|"")
            print_usage
            ;;
        *)
            echo -e "${RED}❌ Unknown command: $command${NC}"
            echo ""
            print_usage
            exit 1
            ;;
    esac
}

main "$@" 