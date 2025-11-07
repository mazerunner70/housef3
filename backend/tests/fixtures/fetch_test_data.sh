#!/bin/bash
# Fetch real transaction data from DynamoDB for testing
# Usage: ./fetch_test_data.sh [user_id]

set -e

USER_ID="${1:-}"
OUTPUT_DIR="$(dirname "$0")/data"

if [ -z "$USER_ID" ]; then
    echo "Usage: $0 <user_id>"
    echo "Fetches real transaction data from DynamoDB for testing"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Get table name from environment or use default
TRANSACTIONS_TABLE="${TRANSACTIONS_TABLE:-housef3-transactions}"

echo "Fetching transactions for user: $USER_ID"
echo "Table: $TRANSACTIONS_TABLE"

# Fetch transactions for the user (limit to 100 for testing)
aws dynamodb query \
    --table-name "$TRANSACTIONS_TABLE" \
    --key-condition-expression "userId = :userId" \
    --expression-attribute-values "{\":userId\":{\"S\":\"$USER_ID\"}}" \
    --limit 100 \
    --output json > "$OUTPUT_DIR/transactions_raw.json"

# Extract just the Items array and save
cat "$OUTPUT_DIR/transactions_raw.json" | jq '.Items' > "$OUTPUT_DIR/transactions.json"

# Count transactions
TRANSACTION_COUNT=$(cat "$OUTPUT_DIR/transactions.json" | jq 'length')
echo "Fetched $TRANSACTION_COUNT transactions"

# Create a sample of recurring patterns (transactions with similar descriptions)
echo "Analyzing for recurring patterns..."

# Find transactions with "NETFLIX" in description
cat "$OUTPUT_DIR/transactions.json" | jq '[.[] | select(.description.S | test("NETFLIX"; "i"))]' > "$OUTPUT_DIR/netflix_transactions.json"
NETFLIX_COUNT=$(cat "$OUTPUT_DIR/netflix_transactions.json" | jq 'length')
echo "Found $NETFLIX_COUNT Netflix transactions"

# Find transactions with "SPOTIFY" in description
cat "$OUTPUT_DIR/transactions.json" | jq '[.[] | select(.description.S | test("SPOTIFY"; "i"))]' > "$OUTPUT_DIR/spotify_transactions.json"
SPOTIFY_COUNT=$(cat "$OUTPUT_DIR/spotify_transactions.json" | jq 'length')
echo "Found $SPOTIFY_COUNT Spotify transactions"

# Find transactions with "GYM" or "FITNESS" in description
cat "$OUTPUT_DIR/transactions.json" | jq '[.[] | select(.description.S | test("GYM|FITNESS|PLANET"; "i"))]' > "$OUTPUT_DIR/gym_transactions.json"
GYM_COUNT=$(cat "$OUTPUT_DIR/gym_transactions.json" | jq 'length')
echo "Found $GYM_COUNT gym/fitness transactions"

# Find transactions with "SALARY" or "PAYROLL" in description
cat "$OUTPUT_DIR/transactions.json" | jq '[.[] | select(.description.S | test("SALARY|PAYROLL|DEPOSIT.*DIRECT"; "i"))]' > "$OUTPUT_DIR/salary_transactions.json"
SALARY_COUNT=$(cat "$OUTPUT_DIR/salary_transactions.json" | jq 'length')
echo "Found $SALARY_COUNT salary/payroll transactions"

# Create a summary
cat > "$OUTPUT_DIR/summary.json" << EOF
{
  "user_id": "$USER_ID",
  "fetch_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "total_transactions": $TRANSACTION_COUNT,
  "patterns": {
    "netflix": $NETFLIX_COUNT,
    "spotify": $SPOTIFY_COUNT,
    "gym": $GYM_COUNT,
    "salary": $SALARY_COUNT
  }
}
EOF

echo ""
echo "✅ Test data saved to: $OUTPUT_DIR"
echo "Summary:"
cat "$OUTPUT_DIR/summary.json" | jq '.'

