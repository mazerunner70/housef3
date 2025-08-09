#!/bin/bash
set -e

# Script to add test users to Cognito User Pool
# Usage: ./add_cognito_test_user.sh
#
# Users are read from a file named 'test-accounts.env' located at the project root.
# Each non-empty, non-comment line should contain: "email password"
# Comma-separated pairs like "email,password" are also supported.
# NOTE: All accounts are created with permanent passwords (no forced change on first login).
# NOTE: Script will error if any user already exists - manual cleanup required.

# Colors for output (defined early for use in argument parsing)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# No configuration needed - all accounts are permanent by default

# Parse arguments (currently no options supported)
for arg in "$@"; do
    case $arg in
        --*)
            echo -e "${RED}Unknown option: $arg${NC}"
            echo "Usage: ./add_cognito_test_user.sh"
            exit 1
            ;;
    esac
done

echo -e "${YELLOW}Adding test user to Cognito User Pool...${NC}"

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

    # Check if user already exists
    if aws cognito-idp admin-get-user --user-pool-id "$USER_POOL_ID" --username "$USERNAME" >/dev/null 2>&1; then
        echo -e "${RED}❌ User '$USERNAME' already exists - skipping${NC}"
        FAILED_ACCOUNTS=$((FAILED_ACCOUNTS + 1))
        ERRORS+=("User '$USERNAME' already exists in Cognito User Pool")
        continue
    fi

    # Create the user with temporary password
    echo -e "${YELLOW}Creating user with temporary password...${NC}"
    if aws cognito-idp admin-create-user \
        --user-pool-id "$USER_POOL_ID" \
        --username "$USERNAME" \
        --temporary-password "$PASSWORD" \
        --user-attributes Name=email,Value="$EMAIL" Name=email_verified,Value=true \
        --message-action SUPPRESS 2>/dev/null; then
        
        echo -e "${GREEN}User created: $USERNAME${NC}"

        # Set permanent password (all accounts are permanent by default)
        echo -e "${YELLOW}Setting permanent password...${NC}"
        if aws cognito-idp admin-set-user-password \
            --user-pool-id "$USER_POOL_ID" \
            --username "$USERNAME" \
            --password "$PASSWORD" \
            --permanent 2>/dev/null; then
            
            echo -e "${GREEN}✅ Success: $USERNAME ready for immediate login${NC}"
            SUCCESSFUL_ACCOUNTS=$((SUCCESSFUL_ACCOUNTS + 1))
        else
            echo -e "${RED}❌ Error setting permanent password for $USERNAME${NC}"
            FAILED_ACCOUNTS=$((FAILED_ACCOUNTS + 1))
            ERRORS+=("Failed to set permanent password for '$USERNAME'")
        fi
    else
        echo -e "${RED}❌ Error creating user $USERNAME${NC}"
        FAILED_ACCOUNTS=$((FAILED_ACCOUNTS + 1))
        ERRORS+=("Failed to create user '$USERNAME'")
    fi
done < "$ACCOUNTS_FILE"

echo ""
echo "=================================="
echo -e "${GREEN}📊 ACCOUNT CREATION SUMMARY${NC}"
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
    echo -e "${GREEN}✅ $SUCCESSFUL_ACCOUNTS account(s) ready for immediate login${NC}"
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