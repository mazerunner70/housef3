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

# Get the values from terraform output
cd "$PROJECT_ROOT/infrastructure/terraform" || exit 1
CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_distribution_domain)
CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)

# Authenticate user and get token
echo "Authenticating user..."
AUTH_RESULT=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters USERNAME=$USERNAME,PASSWORD=$PASSWORD)

ID_TOKEN=$(echo $AUTH_RESULT | jq -r '.AuthenticationResult.IdToken')

# Get the test user's Cognito ID
echo "Fetching test user's Cognito ID..."
USER_ID=$(aws cognito-idp list-users \
    --user-pool-id $USER_POOL_ID \
    --filter "email = \"usecase@example.com\"" \
    --query "Users[0].Username" \
    --output text)

if [ -z "$USER_ID" ] || [ "$USER_ID" = "None" ]; then
    echo "Error: Could not find test user in Cognito"
    exit 1
fi

echo "Cleaning up resources for user: $USER_ID"

# List and delete accounts
echo "Listing accounts..."
ACCOUNTS_RESPONSE=$(curl -s -H "Authorization: $ID_TOKEN" "https://$CLOUDFRONT_DOMAIN/api/accounts")
echo "Accounts response: $ACCOUNTS_RESPONSE"

# If the response is HTML, it means the endpoint doesn't exist
if [[ "$ACCOUNTS_RESPONSE" == *"<!doctype html>"* ]]; then
    echo "Accounts endpoint not found or not accessible"
else
    # Try to extract account IDs from the response
    ACCOUNTS=$(echo "$ACCOUNTS_RESPONSE" | jq -r '.accounts[]?.accountId // empty')
    
    if [ -n "$ACCOUNTS" ]; then
        echo "Deleting accounts..."
        for ACCOUNT_ID in $ACCOUNTS; do
            echo "Deleting account: $ACCOUNT_ID"
            curl -X DELETE "https://$CLOUDFRONT_DOMAIN/api/accounts/$ACCOUNT_ID" \
                -H "Authorization: $ID_TOKEN" \
                -H "Content-Type: application/json"
        done
    else
        echo "No accounts found to delete"
    fi
fi

# List files and delete their transactions first
echo "Listing files..."
FILES_RESPONSE=$(curl -s -H "Authorization: $ID_TOKEN" "https://$CLOUDFRONT_DOMAIN/api/files")
echo "Files response: $FILES_RESPONSE"

# If the response is HTML, it means the endpoint doesn't exist
if [[ "$FILES_RESPONSE" == *"<!doctype html>"* ]]; then
    echo "Files endpoint not found or not accessible"
else
    # Try to extract file IDs from the response
    FILES=$(echo "$FILES_RESPONSE" | jq -r '.files[]?.fileId // empty')
    
    if [ -n "$FILES" ]; then
        echo "Processing files..."
        for FILE_ID in $FILES; do
            echo "Processing file: $FILE_ID"
            
            # Delete transactions for this file
            echo "Deleting transactions for file: $FILE_ID"
            TRANSACTIONS_RESPONSE=$(curl -s -H "Authorization: $ID_TOKEN" "https://$CLOUDFRONT_DOMAIN/api/files/$FILE_ID/transactions")
            echo "Transactions response: $TRANSACTIONS_RESPONSE"
            
            if [[ "$TRANSACTIONS_RESPONSE" != *"<!doctype html>"* ]]; then
                TRANSACTIONS=$(echo "$TRANSACTIONS_RESPONSE" | jq -r '.transactions[]?.transactionId // empty')
                if [ -n "$TRANSACTIONS" ]; then
                    for TRANSACTION_ID in $TRANSACTIONS; do
                        echo "Deleting transaction: $TRANSACTION_ID"
                        curl -X DELETE "https://$CLOUDFRONT_DOMAIN/api/files/$FILE_ID/transactions/$TRANSACTION_ID" \
                            -H "Authorization: $ID_TOKEN" \
                            -H "Content-Type: application/json"
                    done
                else
                    echo "No transactions found for file: $FILE_ID"
                fi
            fi
            
            # Delete the file itself
            echo "Deleting file: $FILE_ID"
            curl -X DELETE "https://$CLOUDFRONT_DOMAIN/api/files/$FILE_ID" \
                -H "Authorization: $ID_TOKEN" \
                -H "Content-Type: application/json"
        done
    else
        echo "No files found to delete"
    fi
fi

echo "Cleanup complete!" 