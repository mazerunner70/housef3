#!/bin/bash
set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
CONFIG_FILE="$SCRIPT_DIR/config.json"
DATA_DIR="$SCRIPT_DIR/usecase_data"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found at $CONFIG_FILE"
    exit 1
fi

# Read credentials from config file
USERNAME=$(jq -r '.username' "$CONFIG_FILE")
PASSWORD=$(jq -r '.password' "$CONFIG_FILE")

# Source the environment variables
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

# Process each subfolder in usecase_data
for SUBFOLDER in "$DATA_DIR"/*/; do
    if [ ! -d "$SUBFOLDER" ]; then
        continue
    fi

    # Get account name from subfolder name (remove trailing slash and convert to title case)
    ACCOUNT_NAME=$(basename "$SUBFOLDER" | sed 's/-/ /g' | sed 's/\b\(.\)/\u\1/g')
    echo "Processing account: $ACCOUNT_NAME"

    # Create account
    echo "Creating account..."
    ACCOUNT_RESPONSE=$(curl -s -X POST "https://${CLOUDFRONT_DOMAIN}/api/accounts" \
        -H "Authorization: Bearer ${ID_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
            \"accountName\": \"$ACCOUNT_NAME\",
            \"accountType\": \"credit_card\",
            \"currency\": \"GBP\",
            \"institution\": \"Virgin Money\"
        }")

    ACCOUNT_ID=$(echo "$ACCOUNT_RESPONSE" | jq -r '.account.accountId')
    if [ -z "$ACCOUNT_ID" ] || [ "$ACCOUNT_ID" = "null" ]; then
        echo "Error: Failed to create account"
        echo "Response: $ACCOUNT_RESPONSE"
        exit 1
    fi
    echo "Created account with ID: $ACCOUNT_ID"

    # Process each file in the subfolder
    for FILE in "$SUBFOLDER"*.csv; do
        if [ ! -f "$FILE" ]; then
            continue
        fi

        FILE_NAME=$(basename "$FILE")
        echo "Processing file: $FILE_NAME"

        # Get upload URL
        echo "Getting upload URL..."
        UPLOAD_URL_RESPONSE=$(curl -s -X POST "https://${CLOUDFRONT_DOMAIN}/api/files/upload" \
            -H "Authorization: Bearer ${ID_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "{\"fileName\": \"$FILE_NAME\"}")

        echo "Upload URL Response: $UPLOAD_URL_RESPONSE"

        UPLOAD_URL=$(echo "$UPLOAD_URL_RESPONSE" | jq -r '.uploadUrl')
        FILE_ID=$(echo "$UPLOAD_URL_RESPONSE" | jq -r '.fileId')

        if [ -z "$UPLOAD_URL" ] || [ "$UPLOAD_URL" = "null" ]; then
            echo "Error: Failed to get upload URL"
            echo "Response: $UPLOAD_URL_RESPONSE"
            exit 1
        fi

        # Upload file
        echo "Uploading file..."
        curl -s -X PUT "$UPLOAD_URL" \
            -H "Content-Type: text/csv" \
            --data-binary "@$FILE"

        # Associate file with account
        echo "Associating file with account..."
        curl -s -X POST "https://${CLOUDFRONT_DOMAIN}/api/accounts/${ACCOUNT_ID}/files" \
            -H "Authorization: Bearer ${ID_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "{\"fileId\": \"$FILE_ID\", \"fileName\": \"$FILE_NAME\"}"

        echo "File processed successfully"
    done
done

echo "All files processed successfully!" 