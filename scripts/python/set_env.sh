#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Navigate to Terraform directory
cd "$PROJECT_ROOT/infrastructure/terraform"

# Set AWS region
export AWS_REGION="eu-west-2"

# Get table names from Terraform output
export ACCOUNTS_TABLE=$(terraform output -raw accounts_table_name)
export TRANSACTIONS_TABLE=$(terraform output -raw transactions_table_name)
export FILES_TABLE=$(terraform output -raw transaction_files_table_name)
export ANALYTICS_DATA_TABLE=$(terraform output -raw analytics_data_table_name)
export ANALYTICS_STATUS_TABLE=$(terraform output -raw analytics_status_table_name)

echo "Environment variables set:"
echo "AWS_REGION=$AWS_REGION"
echo "ACCOUNTS_TABLE=$ACCOUNTS_TABLE"
echo "TRANSACTIONS_TABLE=$TRANSACTIONS_TABLE"
echo "FILES_TABLE=$FILES_TABLE"
echo "ANALYTICS_DATA_TABLE=$ANALYTICS_DATA_TABLE"
echo "ANALYTICS_STATUS_TABLE=$ANALYTICS_STATUS_TABLE"

# Return to original directory
cd - > /dev/null 