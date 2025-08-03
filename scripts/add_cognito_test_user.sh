#!/bin/bash
set -e

# Script to add a test user to Cognito User Pool
# Usage: ./add_cognito_test_user.sh [password] [--permanent]

# Default values
USERNAME="usecase@example.com"
EMAIL="usecase@example.com"
PASSWORD="${1:-TempPassword123!}"
PERMANENT="${2}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Adding test user to Cognito User Pool...${NC}"

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Navigate to terraform directory to get outputs
cd "$PROJECT_ROOT/infrastructure/terraform"

# Get Cognito User Pool ID from Terraform outputs
USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)

if [ -z "$USER_POOL_ID" ]; then
    echo -e "${RED}Error: Could not get Cognito User Pool ID from Terraform outputs${NC}"
    exit 1
fi

echo "User Pool ID: $USER_POOL_ID"
echo "Username: $USERNAME"
echo "Email: $EMAIL"

# Check if user already exists
if aws cognito-idp admin-get-user --user-pool-id "$USER_POOL_ID" --username "$USERNAME" >/dev/null 2>&1; then
    echo -e "${YELLOW}User already exists. Deleting existing user first...${NC}"
    aws cognito-idp admin-delete-user \
        --user-pool-id "$USER_POOL_ID" \
        --username "$USERNAME"
    echo -e "${GREEN}Existing user deleted.${NC}"
fi

# Create the user with temporary password
echo -e "${YELLOW}Creating user with temporary password...${NC}"
aws cognito-idp admin-create-user \
    --user-pool-id "$USER_POOL_ID" \
    --username "$USERNAME" \
    --temporary-password "$PASSWORD" \
    --user-attributes Name=email,Value="$EMAIL" Name=email_verified,Value=true \
    --message-action SUPPRESS

echo -e "${GREEN}User created successfully!${NC}"

# If --permanent flag is provided, set permanent password
if [ "$PERMANENT" = "--permanent" ]; then
    echo -e "${YELLOW}Setting permanent password...${NC}"
    aws cognito-idp admin-set-user-password \
        --user-pool-id "$USER_POOL_ID" \
        --username "$USERNAME" \
        --password "$PASSWORD" \
        --permanent
    echo -e "${GREEN}Permanent password set. User can login immediately.${NC}"
else
    echo -e "${YELLOW}User created with temporary password. User will need to change password on first login.${NC}"
fi

echo ""
echo -e "${GREEN}✅ Test user setup complete!${NC}"
echo -e "${GREEN}Username: $USERNAME${NC}"
echo -e "${GREEN}Password: $PASSWORD${NC}"
if [ "$PERMANENT" = "--permanent" ]; then
    echo -e "${GREEN}Status: Ready to use immediately${NC}"
else
    echo -e "${YELLOW}Status: Must change password on first login${NC}"
fi

# Get additional Cognito info for reference
CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
echo ""
echo -e "${YELLOW}Cognito Configuration:${NC}"
echo "User Pool ID: $USER_POOL_ID"
echo "Client ID: $CLIENT_ID"
echo "Region: $(terraform output -raw | grep aws_region || echo 'eu-west-2')"