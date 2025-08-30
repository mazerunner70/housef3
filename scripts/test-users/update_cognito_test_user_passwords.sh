#!/bin/bash
set -e

# Script to update passwords for existing test users in Cognito User Pool
# Usage: ./update_cognito_test_user_passwords.sh
#
# Users are read from a file named 'test-accounts.env' located at the project root.
# Each non-empty, non-comment line should contain: "email password"
# Comma-separated pairs like "email,password" are also supported.
# NOTE: All passwords are set as permanent (no forced change on first login).
# NOTE: Script will attempt to update all users, showing errors for any that don't exist.

# Colors for output (defined early for use in argument parsing)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments (currently no options supported)
for arg in "$@"; do
    case $arg in
        --*)
            echo -e "${RED}Unknown option: $arg${NC}"
            echo "Usage: ./update_cognito_test_user_passwords.sh"
            exit 1
            ;;
    esac
done

echo -e "${YELLOW}Updating test user passwords in Cognito User Pool...${NC}"

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Navigate to terraform directory to get outputs
cd "$PROJECT_ROOT/infrastructure/terraform"

# Get Cognito User Pool ID from Terraform outputs
USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)

if [ -z "$USER_POOL_ID" ]; then
    echo -e "${RED}Error: Could not get Cognito User Pool ID from Terraform outputs${NC}"
    exit 1
fi

echo "User Pool ID: $USER_POOL_ID"

# Determine accounts file path
ACCOUNTS_FILE="${ACCOUNTS_FILE:-$PROJECT_ROOT/test-accounts.env}"

if [ ! -f "$ACCOUNTS_FILE" ]; then
    echo -e "${RED}Error: Accounts file not found: $ACCOUNTS_FILE${NC}"
    echo "Create it with lines like: 'user@example.com StrongPassw0rd!'"
    exit 1
fi

echo -e "${YELLOW}Reading accounts from: $ACCOUNTS_FILE${NC}"

# Track results
TOTAL_ACCOUNTS=0
SUCCESSFUL_ACCOUNTS=0
FAILED_ACCOUNTS=0
ERRORS=()

# Process each account line
while IFS= read -r line || [ -n "$line" ]; do
    # Trim whitespace
    trimmed_line="$(echo "$line" | sed -e 's/^\s\+//' -e 's/\s\+$//')"
    # Skip comments and empty lines
    if [ -z "$trimmed_line" ] || [[ "$trimmed_line" =~ ^# ]]; then
        continue
    fi

    # Support comma or whitespace separation
    EMAIL="$(echo "$trimmed_line" | awk -F'[[:space:],]+' '{print $1}')"
    PASSWORD="$(echo "$trimmed_line" | awk -F'[[:space:],]+' '{print $2}')"

    if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
        echo -e "${RED}Skipping malformed line: $line${NC}"
        FAILED_ACCOUNTS=$((FAILED_ACCOUNTS + 1))
        ERRORS+=("Malformed line: $line")
        continue
    fi

    USERNAME="$EMAIL"
    TOTAL_ACCOUNTS=$((TOTAL_ACCOUNTS + 1))
    echo ""
    echo -e "${YELLOW}Processing user $TOTAL_ACCOUNTS: $USERNAME${NC}"

    # Check if user exists
    if ! aws cognito-idp admin-get-user --user-pool-id "$USER_POOL_ID" --username "$USERNAME" >/dev/null 2>&1; then
        echo -e "${RED}❌ User '$USERNAME' does not exist - skipping${NC}"
        FAILED_ACCOUNTS=$((FAILED_ACCOUNTS + 1))
        ERRORS+=("User '$USERNAME' does not exist in Cognito User Pool")
        continue
    fi

    # Update the user password to permanent
    echo -e "${YELLOW}Updating password for existing user...${NC}"
    if aws cognito-idp admin-set-user-password \
        --user-pool-id "$USER_POOL_ID" \
        --username "$USERNAME" \
        --password "$PASSWORD" \
        --permanent 2>/dev/null; then
        
        echo -e "${GREEN}✅ Success: Password updated for $USERNAME${NC}"
        SUCCESSFUL_ACCOUNTS=$((SUCCESSFUL_ACCOUNTS + 1))
    else
        echo -e "${RED}❌ Error updating password for $USERNAME${NC}"
        FAILED_ACCOUNTS=$((FAILED_ACCOUNTS + 1))
        ERRORS+=("Failed to update password for '$USERNAME'")
    fi
done < "$ACCOUNTS_FILE"

echo ""
echo "=================================="
echo -e "${GREEN}📊 PASSWORD UPDATE SUMMARY${NC}"
echo "=================================="
echo "Total accounts processed: $TOTAL_ACCOUNTS"
echo -e "${GREEN}Successful: $SUCCESSFUL_ACCOUNTS${NC}"
echo -e "${RED}Failed: $FAILED_ACCOUNTS${NC}"

if [ ${#ERRORS[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ ERRORS ENCOUNTERED:${NC}"
    for error in "${ERRORS[@]}"; do
        echo -e "${RED}  • $error${NC}"
    done
fi

if [ $SUCCESSFUL_ACCOUNTS -gt 0 ]; then
    echo ""
    echo -e "${GREEN}✅ $SUCCESSFUL_ACCOUNTS password(s) updated successfully${NC}"
fi

# Get additional Cognito info for reference
CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
echo ""
echo -e "${YELLOW}Cognito Configuration:${NC}"
echo "User Pool ID: $USER_POOL_ID"
echo "Client ID: $CLIENT_ID"
echo "Region: eu-west-2"

# Exit with error code if any accounts failed
if [ $FAILED_ACCOUNTS -gt 0 ]; then
    exit 1
fi
