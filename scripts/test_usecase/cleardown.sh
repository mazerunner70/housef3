#!/bin/bash
set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
CONFIG_FILE="$SCRIPT_DIR/config.json"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found at $CONFIG_FILE"
    exit 1
fi

# Read credentials from config file
USERNAME=$(jq -r '.username' "$CONFIG_FILE")
PASSWORD=$(jq -r '.password' "$CONFIG_FILE")

# Source environment variables
source "$SCRIPT_DIR/setup_test_env.sh"

# Authenticate user and get token
echo "Authenticating user..."
AUTH_RESULT=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_CLIENT_ID \
  --auth-parameters USERNAME=$USERNAME,PASSWORD=$PASSWORD)

ID_TOKEN=$(echo $AUTH_RESULT | jq -r '.AuthenticationResult.IdToken')

if [ -z "$ID_TOKEN" ] || [ "$ID_TOKEN" = "null" ]; then
    echo "Error: Failed to get ID token"
    exit 1
fi

# Get the test user's Cognito ID
echo "Fetching test user's Cognito ID..."
USER_ID=$(aws cognito-idp list-users \
    --user-pool-id $COGNITO_USER_POOL_ID \
    --filter "username = \"$USERNAME\"" \
    --query 'Users[0].Username' \
    --output text)

if [ -z "$USER_ID" ] || [ "$USER_ID" = "null" ]; then
    echo "Error: Failed to get user ID"
    exit 1
fi

echo "Cleaning up resources for user: $USER_ID"

# Get all accounts for the user
echo "Fetching accounts..."
ACCOUNTS_RESPONSE=$(curl -s -X GET "https://${CLOUDFRONT_DOMAIN}/api/accounts" \
    -H "Authorization: Bearer ${ID_TOKEN}")

ACCOUNTS=$(echo "$ACCOUNTS_RESPONSE" | jq -r '.accounts')
ACCOUNT_COUNT=$(echo "$ACCOUNTS" | jq 'length')
echo "Found $ACCOUNT_COUNT accounts to delete"

TOTAL_FILES=0
TOTAL_TRANSACTIONS=0

# For each account, get its files and transactions
for i in $(seq 0 $(($ACCOUNT_COUNT - 1))); do
    ACCOUNT_ID=$(echo "$ACCOUNTS" | jq -r ".[$i].accountId")
    
    # Get files for this account
    FILES_RESPONSE=$(curl -s -X GET "https://${CLOUDFRONT_DOMAIN}/api/accounts/${ACCOUNT_ID}/files" \
        -H "Authorization: Bearer ${ID_TOKEN}")
    
    FILES=$(echo "$FILES_RESPONSE" | jq -r '.files')
    FILE_COUNT=$(echo "$FILES" | jq 'length')
    TOTAL_FILES=$((TOTAL_FILES + FILE_COUNT))
    
    # For each file, get its transactions
    for j in $(seq 0 $(($FILE_COUNT - 1))); do
        FILE_ID=$(echo "$FILES" | jq -r ".[$j].fileId")
        
        TRANSACTIONS_RESPONSE=$(curl -s -X GET "https://${CLOUDFRONT_DOMAIN}/api/files/${FILE_ID}/transactions" \
            -H "Authorization: Bearer ${ID_TOKEN}")
        
        TRANSACTIONS=$(echo "$TRANSACTIONS_RESPONSE" | jq -r '.transactions')
        TRANSACTION_COUNT=$(echo "$TRANSACTIONS" | jq 'length')
        TOTAL_TRANSACTIONS=$((TOTAL_TRANSACTIONS + TRANSACTION_COUNT))
    done
done

# Get all files for the user (including those not associated with accounts)
echo "Fetching all files for user..."
ALL_FILES_RESPONSE=$(curl -s -X GET "https://${CLOUDFRONT_DOMAIN}/api/files" \
    -H "Authorization: Bearer ${ID_TOKEN}")

ALL_FILES=$(echo "$ALL_FILES_RESPONSE" | jq -r '.files')
ALL_FILE_COUNT=$(echo "$ALL_FILES" | jq 'length')
echo "Found $ALL_FILE_COUNT total files (including those not associated with accounts)"

# Calculate files not associated with accounts
UNASSOCIATED_FILES=$((ALL_FILE_COUNT - TOTAL_FILES))
echo "Found $UNASSOCIATED_FILES files not associated with accounts"

echo "Summary of resources to be deleted:"
echo "- Accounts: $ACCOUNT_COUNT"
echo "- Files associated with accounts: $TOTAL_FILES"
echo "- Files not associated with accounts: $UNASSOCIATED_FILES"
echo "- Transactions: $TOTAL_TRANSACTIONS"

read -p "Do you want to proceed with deletion? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Deletion cancelled"
    exit 0
fi

echo "Deleting all accounts and their files..."

# Delete all accounts
for i in $(seq 0 $(($ACCOUNT_COUNT - 1))); do
    ACCOUNT_ID=$(echo "$ACCOUNTS" | jq -r ".[$i].accountId")
    echo "Deleting account: $ACCOUNT_ID"
    
    # Delete the account
    curl -s -X DELETE "https://${CLOUDFRONT_DOMAIN}/api/accounts/${ACCOUNT_ID}" \
        -H "Authorization: Bearer ${ID_TOKEN}"
done

# Delete files not associated with accounts
if [ $UNASSOCIATED_FILES -gt 0 ]; then
    echo "Deleting files not associated with accounts..."
    for i in $(seq 0 $(($ALL_FILE_COUNT - 1))); do
        FILE_ID=$(echo "$ALL_FILES" | jq -r ".[$i].fileId")
        FILE_NAME=$(echo "$ALL_FILES" | jq -r ".[$i].fileName")
        
        # Check if this file is associated with any account
        IS_ASSOCIATED=false
        for j in $(seq 0 $(($ACCOUNT_COUNT - 1))); do
            ACCOUNT_ID=$(echo "$ACCOUNTS" | jq -r ".[$j].accountId")
            FILES_RESPONSE=$(curl -s -X GET "https://${CLOUDFRONT_DOMAIN}/api/accounts/${ACCOUNT_ID}/files" \
                -H "Authorization: Bearer ${ID_TOKEN}")
            ASSOCIATED_FILES=$(echo "$FILES_RESPONSE" | jq -r '.files')
            if echo "$ASSOCIATED_FILES" | jq -e ".[] | select(.fileId == \"$FILE_ID\")" > /dev/null; then
                IS_ASSOCIATED=true
                break
            fi
        done
        
        if [ "$IS_ASSOCIATED" = false ]; then
            echo "Deleting unassociated file: $FILE_NAME"
            curl -s -X DELETE "https://${CLOUDFRONT_DOMAIN}/api/files/${FILE_ID}" \
                -H "Authorization: Bearer ${ID_TOKEN}"
        fi
    done
fi

echo "Cleanup completed successfully!" 