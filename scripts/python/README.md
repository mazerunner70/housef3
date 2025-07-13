# Python Scripts

This directory contains Python scripts for managing and maintaining the housef3 application.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Available Scripts

### update_last_transaction_dates.py
Updates the last transaction date for all accounts in the system. This is a one-time migration script to populate the new `last_transaction_date` field.

Usage:
```bash
python update_last_transaction_dates.py
```

## Environment Variables

The scripts expect the following environment variables to be set:
- `AWS_REGION`: AWS region (e.g., eu-west-2)
- `ACCOUNTS_TABLE`: DynamoDB table name for accounts
- `TRANSACTIONS_TABLE`: DynamoDB table name for transactions

These can be set automatically by running:
```bash
source ../../infrastructure/set_env.sh
``` 