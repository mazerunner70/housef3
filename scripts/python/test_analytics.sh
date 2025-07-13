#!/bin/bash

# Set up environment
source $(dirname "$0")/set_env.sh

# Test user ID - this should match a user in your system
USER_ID="2602f254-70f1-7064-c637-fd69dbe4e8b3"

# Test analytics for last 12 months
echo "Testing analytics for last 12 months..."
aws dynamodb query \
  --table-name $ANALYTICS_DATA_TABLE \
  --key-condition-expression "pk = :pk" \
  --expression-attribute-values '{":pk": {"S": "'$USER_ID'#cash_flow"}}' \
  --region $AWS_REGION | jq .

# Test analytics for current month
echo -e "\nTesting analytics for current month..."
CURRENT_MONTH=$(date +%Y-%m)
aws dynamodb query \
  --table-name $ANALYTICS_DATA_TABLE \
  --key-condition-expression "pk = :pk AND begins_with(sk, :sk)" \
  --expression-attribute-values '{
    ":pk": {"S": "'$USER_ID'#cash_flow"},
    ":sk": {"S": "'$CURRENT_MONTH'"}
  }' \
  --region $AWS_REGION | jq .

# Test analytics for previous month
echo -e "\nTesting analytics for previous month..."
PREV_MONTH=$(date -d "last month" +%Y-%m)
aws dynamodb query \
  --table-name $ANALYTICS_DATA_TABLE \
  --key-condition-expression "pk = :pk AND begins_with(sk, :sk)" \
  --expression-attribute-values '{
    ":pk": {"S": "'$USER_ID'#cash_flow"},
    ":sk": {"S": "'$PREV_MONTH'"}
  }' \
  --region $AWS_REGION | jq .

# Test raw transactions for the period
echo -e "\nTesting raw transactions for last 12 months..."
START_DATE=$(date -d "12 months ago" +%s%3N)  # milliseconds since epoch
END_DATE=$(date +%s%3N)  # current time in milliseconds
aws dynamodb scan \
  --table-name $TRANSACTIONS_TABLE \
  --filter-expression "userId = :uid AND #date BETWEEN :start AND :end" \
  --expression-attribute-names '{"#date": "date"}' \
  --expression-attribute-values '{
    ":uid": {"S": "'$USER_ID'"},
    ":start": {"N": "'$START_DATE'"},
    ":end": {"N": "'$END_DATE'"}
  }' \
  --region $AWS_REGION | jq '.Items | length' 