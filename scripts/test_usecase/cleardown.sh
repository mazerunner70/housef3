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

# Set up API endpoint
API_ENDPOINT="https://${CLOUDFRONT_DOMAIN}/api"
echo "Using API endpoint: $API_ENDPOINT"

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
ACCOUNTS_RESPONSE=$(curl -s -X GET "${API_ENDPOINT}/accounts" \
    -H "Authorization: Bearer ${ID_TOKEN}")

ACCOUNTS=$(echo "$ACCOUNTS_RESPONSE" | jq -r '.accounts')
ACCOUNT_COUNT=$(echo "$ACCOUNTS" | jq 'length')
echo "Found $ACCOUNT_COUNT accounts to delete"

TOTAL_FILES=0
TOTAL_TRANSACTIONS=0
ORPHANED_TRANSACTIONS=0

# For each account, get its files and transactions
for i in $(seq 0 $(($ACCOUNT_COUNT - 1))); do
    ACCOUNT_ID=$(echo "$ACCOUNTS" | jq -r ".[$i].accountId")
    
    # Get files for this account
    FILES_RESPONSE=$(curl -s -X GET "${API_ENDPOINT}/accounts/${ACCOUNT_ID}/files" \
        -H "Authorization: Bearer ${ID_TOKEN}")
    
    FILES=$(echo "$FILES_RESPONSE" | jq -r '.files')
    FILE_COUNT=$(echo "$FILES" | jq 'length')
    TOTAL_FILES=$((TOTAL_FILES + FILE_COUNT))
    
    # For each file, get its transactions
    for j in $(seq 0 $(($FILE_COUNT - 1))); do
        FILE_ID=$(echo "$FILES" | jq -r ".[$j].fileId")
        
        TRANSACTIONS_RESPONSE=$(curl -s -X GET "${API_ENDPOINT}/files/${FILE_ID}/transactions" \
            -H "Authorization: Bearer ${ID_TOKEN}")
        
        TRANSACTIONS=$(echo "$TRANSACTIONS_RESPONSE" | jq -r '.transactions')
        TRANSACTION_COUNT=$(echo "$TRANSACTIONS" | jq 'length')
        TOTAL_TRANSACTIONS=$((TOTAL_TRANSACTIONS + TRANSACTION_COUNT))
    done
done

# Get all files for the user (including those not associated with accounts)
echo "Fetching all files for user..."
ALL_FILES_RESPONSE=$(curl -s -X GET "${API_ENDPOINT}/files" \
    -H "Authorization: Bearer ${ID_TOKEN}")

ALL_FILES=$(echo "$ALL_FILES_RESPONSE" | jq -r '.files')
ALL_FILE_COUNT=$(echo "$ALL_FILES" | jq 'length')
echo "Found $ALL_FILE_COUNT total files (including those not associated with accounts)"

# Calculate files not associated with accounts
UNASSOCIATED_FILES=$((ALL_FILE_COUNT - TOTAL_FILES))
echo "Found $UNASSOCIATED_FILES files not associated with accounts"

# Get all transactions for the user
echo "Fetching all transactions for user..."
ALL_TRANSACTIONS_RESPONSE=$(curl -s -X GET "${API_ENDPOINT}/transactions" \
    -H "Authorization: Bearer ${ID_TOKEN}")

echo "Raw API Response:"
echo "$ALL_TRANSACTIONS_RESPONSE"

ALL_TRANSACTIONS=$(echo "$ALL_TRANSACTIONS_RESPONSE" | jq -r '.transactions')
ALL_TRANSACTION_COUNT=$(echo "$ALL_TRANSACTIONS" | jq 'length')

# Find orphaned transactions (transactions not associated with any file)
echo "Finding orphaned transactions..."
for i in $(seq 0 $(($ALL_TRANSACTION_COUNT - 1))); do
    TRANSACTION_ID=$(echo "$ALL_TRANSACTIONS" | jq -r ".[$i].transactionId")
    FILE_ID=$(echo "$ALL_TRANSACTIONS" | jq -r ".[$i].fileId")
    
    # Check if the file exists
    FILE_EXISTS=false
    for j in $(seq 0 $(($ALL_FILE_COUNT - 1))); do
        EXISTING_FILE_ID=$(echo "$ALL_FILES" | jq -r ".[$j].fileId")
        if [ "$FILE_ID" = "$EXISTING_FILE_ID" ]; then
            FILE_EXISTS=true
            break
        fi
    done
    
    if [ "$FILE_EXISTS" = false ]; then
        ORPHANED_TRANSACTIONS=$((ORPHANED_TRANSACTIONS + 1))
    fi
done

echo "Summary of resources to be deleted:"
echo "- Accounts: $ACCOUNT_COUNT"
echo "- Files associated with accounts: $TOTAL_FILES"
echo "- Files not associated with accounts: $UNASSOCIATED_FILES"
echo "- Transactions associated with files: $TOTAL_TRANSACTIONS"
echo "- Orphaned transactions: $ORPHANED_TRANSACTIONS"

read -p "Do you want to proceed with deletion? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Deletion cancelled"
    exit 0
fi

# Delete orphaned transactions first
if [ $ORPHANED_TRANSACTIONS -gt 0 ]; then
    echo "Deleting orphaned transactions..."
    for i in $(seq 0 $(($ALL_TRANSACTION_COUNT - 1))); do
        TRANSACTION_ID=$(echo "$ALL_TRANSACTIONS" | jq -r ".[$i].transactionId")
        FILE_ID=$(echo "$ALL_TRANSACTIONS" | jq -r ".[$i].fileId")
        
        # Check if the file exists
        FILE_EXISTS=false
        for j in $(seq 0 $(($ALL_FILE_COUNT - 1))); do
            EXISTING_FILE_ID=$(echo "$ALL_FILES" | jq -r ".[$j].fileId")
            if [ "$FILE_ID" = "$EXISTING_FILE_ID" ]; then
                FILE_EXISTS=true
                break
            fi
        done
        
        if [ "$FILE_EXISTS" = false ]; then
            echo "Deleting orphaned transaction: $TRANSACTION_ID"
            curl -s -X DELETE "${API_ENDPOINT}/transactions/${TRANSACTION_ID}" \
                -H "Authorization: Bearer ${ID_TOKEN}"
        fi
    done
fi

echo "Deleting all accounts and their files..."

# Delete all accounts
for i in $(seq 0 $(($ACCOUNT_COUNT - 1))); do
    ACCOUNT_ID=$(echo "$ACCOUNTS" | jq -r ".[$i].accountId")
    echo "Deleting account: $ACCOUNT_ID"
    
    # Delete the account
    DELETE_RESPONSE=$(curl -s -X DELETE "${API_ENDPOINT}/accounts/${ACCOUNT_ID}" \
        -H "Authorization: Bearer ${ID_TOKEN}")
    
    # Check if response is valid JSON before parsing
    if echo "$DELETE_RESPONSE" | jq empty 2>/dev/null; then
        echo "$DELETE_RESPONSE" | jq .
    else
        echo "Raw response: $DELETE_RESPONSE"
    fi
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
            FILES_RESPONSE=$(curl -s -X GET "${API_ENDPOINT}/accounts/${ACCOUNT_ID}/files" \
                -H "Authorization: Bearer ${ID_TOKEN}")
            
            # Check if response is valid JSON before parsing
            if echo "$FILES_RESPONSE" | jq empty 2>/dev/null; then
                ASSOCIATED_FILES=$(echo "$FILES_RESPONSE" | jq -r '.files')
                if echo "$ASSOCIATED_FILES" | jq -e ".[] | select(.fileId == \"$FILE_ID\")" > /dev/null; then
                    IS_ASSOCIATED=true
                    break
                fi
            else
                echo "Warning: Invalid JSON response when checking file associations"
                echo "Raw response: $FILES_RESPONSE"
                continue
            fi
        done
        
        if [ "$IS_ASSOCIATED" = false ]; then
            echo "Deleting unassociated file: $FILE_NAME"
            DELETE_RESPONSE=$(curl -s -X DELETE "${API_ENDPOINT}/files/${FILE_ID}" \
                -H "Authorization: Bearer ${ID_TOKEN}")
            
            # Check if response is valid JSON before parsing
            if echo "$DELETE_RESPONSE" | jq empty 2>/dev/null; then
                echo "$DELETE_RESPONSE" | jq .
            else
                echo "Raw response: $DELETE_RESPONSE"
            fi
        fi
    done
fi

echo "Cleanup completed successfully!"

# Verify all resources have been deleted
echo -e "\nVerifying cleanup..."

# Check for remaining accounts
echo "Checking for remaining accounts..."
REMAINING_ACCOUNTS_RESPONSE=$(curl -s -X GET "${API_ENDPOINT}/accounts" \
    -H "Authorization: Bearer ${ID_TOKEN}")

if echo "$REMAINING_ACCOUNTS_RESPONSE" | jq empty 2>/dev/null; then
    REMAINING_ACCOUNTS=$(echo "$REMAINING_ACCOUNTS_RESPONSE" | jq -r '.accounts')
    REMAINING_ACCOUNT_COUNT=$(echo "$REMAINING_ACCOUNTS" | jq 'length')
    if [ "$REMAINING_ACCOUNT_COUNT" -gt 0 ]; then
        echo "⚠️ Warning: Found $REMAINING_ACCOUNT_COUNT accounts still associated with user:"
        echo "$REMAINING_ACCOUNTS" | jq .
    else
        echo "✅ No remaining accounts found"
    fi
else
    echo "Error checking remaining accounts. Response:"
    echo "$REMAINING_ACCOUNTS_RESPONSE"
fi

# Check for remaining files
echo -e "\nChecking for remaining files..."
REMAINING_FILES_RESPONSE=$(curl -s -X GET "${API_ENDPOINT}/files" \
    -H "Authorization: Bearer ${ID_TOKEN}")

if echo "$REMAINING_FILES_RESPONSE" | jq empty 2>/dev/null; then
    REMAINING_FILES=$(echo "$REMAINING_FILES_RESPONSE" | jq -r '.files')
    REMAINING_FILE_COUNT=$(echo "$REMAINING_FILES" | jq 'length')
    if [ "$REMAINING_FILE_COUNT" -gt 0 ]; then
        echo "⚠️ Warning: Found $REMAINING_FILE_COUNT files still associated with user:"
        echo "$REMAINING_FILES" | jq .
    else
        echo "✅ No remaining files found"
    fi
else
    echo "Error checking remaining files. Response:"
    echo "$REMAINING_FILES_RESPONSE"
fi

# Check for remaining transactions
echo -e "\nChecking for remaining transactions..."
REMAINING_TRANSACTIONS_RESPONSE=$(curl -s -X GET "${API_ENDPOINT}/transactions" \
    -H "Authorization: Bearer ${ID_TOKEN}")

if echo "$REMAINING_TRANSACTIONS_RESPONSE" | jq empty 2>/dev/null; then
    REMAINING_TRANSACTIONS=$(echo "$REMAINING_TRANSACTIONS_RESPONSE" | jq -r '.transactions')
    REMAINING_TRANSACTION_COUNT=$(echo "$REMAINING_TRANSACTIONS" | jq 'length')
    if [ "$REMAINING_TRANSACTION_COUNT" -gt 0 ]; then
        echo "⚠️ Warning: Found $REMAINING_TRANSACTION_COUNT transactions still associated with user:"
        echo "$REMAINING_TRANSACTIONS" | jq .
    else
        echo "✅ No remaining transactions found"
    fi
else
    echo "Error checking remaining transactions. Response:"
    echo "$REMAINING_TRANSACTIONS_RESPONSE"
fi

# Final summary
echo -e "\nCleanup verification summary:"
echo "- Remaining accounts: $REMAINING_ACCOUNT_COUNT"
echo "- Remaining files: $REMAINING_FILE_COUNT"
echo "- Remaining transactions: $REMAINING_TRANSACTION_COUNT"

if [ "$REMAINING_ACCOUNT_COUNT" -eq 0 ] && [ "$REMAINING_FILE_COUNT" -eq 0 ] && [ "$REMAINING_TRANSACTION_COUNT" -eq 0 ]; then
    echo -e "\n✅ All resources successfully cleaned up!"
    exit 0
else
    echo -e "\n❌ Error: Some resources still exist after cleanup:"
    if [ "$REMAINING_ACCOUNT_COUNT" -gt 0 ]; then
        echo "  - $REMAINING_ACCOUNT_COUNT accounts remaining"
    fi
    if [ "$REMAINING_FILE_COUNT" -gt 0 ]; then
        echo "  - $REMAINING_FILE_COUNT files remaining"
    fi
    if [ "$REMAINING_TRANSACTION_COUNT" -gt 0 ]; then
        echo "  - $REMAINING_TRANSACTION_COUNT transactions remaining"
    fi
    echo "Please check the logs above for detailed information about remaining resources."
    exit 1
fi 