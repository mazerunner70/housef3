# Test Fixtures - Real Transaction Descriptions

This directory contains scripts to help harvest real transaction descriptions from DynamoDB.

## Overview

Tests use **hard-coded** transaction descriptions harvested from real DynamoDB data. This gives us realistic test data without any database connections during test execution.

The scripts here are utilities to help you harvest new descriptions when needed.

## How It Works

Tests contain hard-coded descriptions like:

```python
REAL_DESCRIPTIONS = {
    'netflix': [
        "NETFLIX.COM",
        "NETFLIX SUBSCRIPTION",
        "NETFLIX MONTHLY",
        "NETFLIX.COM CA",
        "NETFLIX *STREAMING",
    ],
    'spotify': [
        "SPOTIFY USA",
        "SPOTIFY P0123456789",
        "SPOTIFY PREMIUM",
    ],
    # ... more patterns
}
```

These descriptions were harvested once from real DynamoDB data and are now part of the test code.

## Updating Descriptions (Rarely Needed)

If you need to harvest new descriptions:

### Step 1: Fetch Sample Data

```bash
./fetch_test_data.sh <user_id>
```

This queries DynamoDB and saves JSON files to `data/`.

### Step 2: Extract Descriptions

```bash
# View Netflix descriptions
cat data/netflix_transactions.json | jq '.[].description.S' | sort | uniq

# View Spotify descriptions  
cat data/spotify_transactions.json | jq '.[].description.S' | sort | uniq
```

### Step 3: Update Test Files

Manually copy interesting descriptions into the test files:
- `tests/services/test_recurring_charge_detection_service.py`
- `tests/integration/test_recurring_charge_end_to_end.py`

## Files in data/ (temporary)

After running fetch script:

```
data/
├── summary.json                    # Summary of fetched data
├── transactions.json               # All transactions (DynamoDB format)
├── netflix_transactions.json       # Netflix transactions only
├── spotify_transactions.json       # Spotify transactions only
├── gym_transactions.json           # Gym/fitness transactions only
└── salary_transactions.json        # Salary/payroll transactions only
```

**Note:** These are temporary files for harvesting descriptions. They are gitignored.

## Environment Variables

- `TRANSACTIONS_TABLE`: DynamoDB table name (default: `housef3-transactions`)

```bash
export TRANSACTIONS_TABLE=my-transactions-table
./fetch_test_data.sh user123
```

## Requirements

- AWS CLI configured with appropriate credentials
- `jq` for JSON processing
- Python 3.12+

## Key Benefits

✅ **No DB connections during tests** - Tests run fast and don't require AWS credentials  
✅ **Realistic data** - Descriptions come from real transactions  
✅ **Simple** - Just hard-coded strings in test files  
✅ **Privacy-safe** - Only descriptions are used, no amounts or user IDs in tests

## Privacy Note

⚠️ **Important**: 
- The `data/` directory is gitignored
- Never commit real user data
- Only extract descriptions, not amounts or personal info
- Use test/anonymized accounts when possible

## Example Workflow

```bash
# 1. Fetch sample data (rarely needed)
./fetch_test_data.sh test_user_001

# 2. Extract interesting descriptions
cat data/netflix_transactions.json | jq '.[].description.S' | sort | uniq

# 3. Copy descriptions into test files
# Edit: tests/services/test_recurring_charge_detection_service.py
# Add to REAL_DESCRIPTIONS dict

# 4. Clean up
rm -rf data/

# 5. Run tests (no DB connection needed!)
cd ../..
python3 -m pytest tests/services/test_recurring_charge_detection_service.py -v
```

## Troubleshooting

### No data fetched
- Verify user_id exists in DynamoDB
- Check AWS credentials: `aws sts get-caller-identity`
- Verify table name: `aws dynamodb list-tables`

### Conversion errors
- Ensure JSON file contains valid DynamoDB items
- Check that all required fields exist (userId, transactionId, date, description, amount)

### Tests failing with real data
- Real data may have edge cases not handled by the algorithm
- This is valuable feedback! Use it to improve the detection logic
- Consider filtering or cleaning the data if needed

