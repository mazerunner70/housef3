#!/usr/bin/env python3
import os
import sys
import boto3
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
import uuid

# Add the backend source directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend/src'))

from models.account import Account
from utils.db_utils import get_last_transaction_date

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
ACCOUNTS_TABLE = os.environ.get('ACCOUNTS_TABLE', f'housef3-{ENVIRONMENT}-accounts')

def get_dynamodb_resource():
    """Get the DynamoDB resource."""
    return boto3.resource('dynamodb')

def update_account_last_transaction_date(table, account_id: uuid.UUID) -> None:
    """
    Update an account's last transaction date using the new GSI.
    """
    try:
        # Get the last transaction date using the new GSI
        last_date = get_last_transaction_date(account_id)
        
        if last_date is not None:
            # Update the account with the new last transaction date
            update_expr = "SET lastTransactionDate = :ltd, updatedAt = :ua"
            expr_values = {
                ':ltd': last_date,
                ':ua': int(datetime.now().timestamp() * 1000)
            }
            
            table.update_item(
                Key={'accountId': str(account_id)},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values
            )
            
            logger.info(f"Updated account {account_id} with last transaction date: {last_date}")
        else:
            logger.info(f"No transactions found for account {account_id}")
            
    except Exception as e:
        logger.error(f"Error updating account {account_id}: {str(e)}")

def update_all_accounts():
    """
    Update last transaction dates for all accounts.
    """
    try:
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(ACCOUNTS_TABLE)
        
        logger.info("Starting account updates...")
        
        # Track statistics
        total_processed = 0
        error_count = 0
        
        # Scan all accounts
        scan_kwargs = {
            'Select': 'ALL_ATTRIBUTES'
        }
        
        while True:
            response = table.scan(**scan_kwargs)
            items = response.get('Items', [])
            
            if not items:
                break
                
            # Process each account
            for item in items:
                try:
                    account_id = uuid.UUID(item['accountId'])
                    update_account_last_transaction_date(table, account_id)
                    total_processed += 1
                    
                    if total_processed % 10 == 0:
                        logger.info(f"Processed {total_processed} accounts")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error processing account {item.get('accountId', 'unknown')}: {str(e)}")
                    continue
            
            # Check if we need to paginate
            if 'LastEvaluatedKey' in response:
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            else:
                break
        
        logger.info(f"Account updates completed!")
        logger.info(f"Total accounts processed: {total_processed}")
        logger.info(f"Total errors encountered: {error_count}")
        
    except Exception as e:
        logger.error(f"Update process failed: {str(e)}")
        raise

if __name__ == "__main__":
    update_all_accounts() 