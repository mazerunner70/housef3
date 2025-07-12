#!/usr/bin/env python3
import os
import sys
import boto3
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
import uuid
from botocore.exceptions import ClientError
import psutil
from boto3.dynamodb.conditions import Key

# Add the backend source directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend/src'))

from models.account import Account
from utils.db_utils import get_latest_transaction, initialize_tables
from models.transaction import Transaction
from .diagnostic import check_table_exists, get_table_info, initialize_dynamodb, get_dynamodb_resource

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'housef3')
AWS_REGION = os.environ.get('AWS_REGION', 'eu-west-2')

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)

# Set the table names in the environment for db_utils
os.environ['ACCOUNTS_TABLE'] = f"{PROJECT_NAME}-{ENVIRONMENT}-accounts"
os.environ['TRANSACTIONS_TABLE'] = f"{PROJECT_NAME}-{ENVIRONMENT}-transactions"
os.environ['FILES_TABLE'] = f"{PROJECT_NAME}-{ENVIRONMENT}-transaction-files"
os.environ['FILE_MAPS_TABLE'] = f"{PROJECT_NAME}-{ENVIRONMENT}-file-maps"
os.environ['CATEGORIES_TABLE_NAME'] = f"{PROJECT_NAME}-{ENVIRONMENT}-categories"
os.environ['ANALYTICS_DATA_TABLE'] = f"{PROJECT_NAME}-{ENVIRONMENT}-analytics-data"
os.environ['ANALYTICS_STATUS_TABLE'] = f"{PROJECT_NAME}-{ENVIRONMENT}-analytics-status"

ACCOUNTS_TABLE = os.environ['ACCOUNTS_TABLE']
TRANSACTIONS_TABLE = os.environ['TRANSACTIONS_TABLE']

logger.info(f"Using tables - Accounts: {ACCOUNTS_TABLE}, Transactions: {TRANSACTIONS_TABLE}")

def get_latest_transaction_balance(account_id: uuid.UUID) -> Optional[Decimal]:
    """
    Get the balance from the latest transaction for an account.
    """
    try:
        start_time = datetime.now()
        
        # Query the most recent non-duplicate transaction for this account
        # The statusDate field is a composite key of format "status#timestamp"
        response = dynamodb.Table(TRANSACTIONS_TABLE).query(
            IndexName='AccountStatusDateIndex',
            KeyConditionExpression=Key('accountId').eq(str(account_id)) & Key('statusDate').begins_with('new#'),
            Limit=1,
            ScanIndexForward=False  # Sort in descending order to get most recent first
        )
        
        query_time = (datetime.now() - start_time).total_seconds()
        
        if response.get('Items'):
            transaction = Transaction.from_dynamodb_item(response['Items'][0])
            logger.debug(f"Found latest transaction for account {account_id} in {query_time:.2f} seconds")
            return transaction.balance
            
        logger.debug(f"No balance found for account {account_id} (query time: {query_time:.2f} seconds)")
        return None
        
    except Exception as e:
        logger.error(f"Error getting latest transaction balance for account {account_id}: {str(e)}")
        return None

def update_account_balance(table, account_id: uuid.UUID) -> bool:
    """
    Update an account's balance using the latest transaction.
    Returns True if update was successful.
    """
    try:
        start_time = datetime.now()
        
        # Get the balance from the latest transaction
        latest_balance = get_latest_transaction_balance(account_id)
        
        if latest_balance is not None:
            # Update the account with the new balance
            update_expr = "SET balance = :bal, updatedAt = :ua"
            expr_values = {
                ':bal': latest_balance,
                ':ua': int(datetime.now().timestamp() * 1000)
            }
            
            table.update_item(
                Key={'accountId': str(account_id)},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values
            )
            
            update_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Updated account {account_id} with balance: {latest_balance} (took {update_time:.2f} seconds)")
            return True
        else:
            logger.info(f"No balance found in transactions for account {account_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error updating account {account_id}: {str(e)}")
        return False

def update_all_accounts():
    """
    Update balances for all accounts based on their latest transactions.
    """
    try:
        # Initialize DynamoDB and verify connection
        if not initialize_dynamodb(ACCOUNTS_TABLE, AWS_REGION) or not initialize_dynamodb(TRANSACTIONS_TABLE, AWS_REGION):
            logger.error("Failed to initialize DynamoDB connection. Aborting updates.")
            return

        # Initialize tables through db_utils
        initialize_tables()
        
        # Get DynamoDB resource after successful initialization
        dynamodb = get_dynamodb_resource([ACCOUNTS_TABLE, TRANSACTIONS_TABLE], AWS_REGION)
        if not dynamodb:
            logger.error("Failed to get DynamoDB resource. Aborting updates.")
            return
            
        table = dynamodb.Table(ACCOUNTS_TABLE)
        
        logger.info("Starting account balance updates...")
        
        # Track statistics and performance metrics
        start_time = datetime.now()
        total_processed = 0
        error_count = 0
        updated_count = 0
        skipped_count = 0
        processing_times = []
        
        # Track memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        logger.info(f"Initial memory usage: {initial_memory:.2f} MB")
        
        # Scan all accounts
        scan_kwargs = {
            'Select': 'ALL_ATTRIBUTES'
        }
        
        while True:
            try:
                response = table.scan(**scan_kwargs)
                items = response.get('Items', [])
                
                if not items:
                    break
                    
                batch_start_time = datetime.now()
                logger.info(f"Processing batch of {len(items)} accounts...")
                
                # Process each account
                for item in items:
                    try:
                        account_id = uuid.UUID(item['accountId'])
                        current_balance = item.get('balance')
                        
                        # Update the account balance
                        if update_account_balance(table, account_id):
                            updated_count += 1
                        else:
                            skipped_count += 1
                            
                        total_processed += 1
                        
                        # Log progress periodically
                        if total_processed % 10 == 0:
                            elapsed_time = (datetime.now() - start_time).total_seconds()
                            rate = total_processed / elapsed_time if elapsed_time > 0 else 0
                            logger.info(f"Progress: {total_processed} accounts processed at {rate:.2f} accounts/second")
                            
                            # Log memory usage
                            current_memory = process.memory_info().rss / 1024 / 1024  # MB
                            memory_change = current_memory - initial_memory
                            logger.info(f"Current memory usage: {current_memory:.2f} MB (Change: {memory_change:+.2f} MB)")
                            
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error processing account: {str(e)}")
                        continue
                
                # Calculate and log batch processing time
                batch_time = (datetime.now() - batch_start_time).total_seconds()
                processing_times.append(batch_time)
                logger.info(f"Batch processing time: {batch_time:.2f} seconds")
                
                # Check if we need to paginate
                if 'LastEvaluatedKey' in response:
                    scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
                    logger.info("Moving to next page of results...")
                else:
                    break
                    
            except ClientError as e:
                error_count += 1
                logger.error(f"DynamoDB client error: {str(e)}")
                if 'LastEvaluatedKey' in response:
                    scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
                    logger.info("Attempting to continue with next page despite error...")
                else:
                    break
        
        # Calculate and log final statistics
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        avg_rate = total_processed / total_time if total_time > 0 else 0
        avg_batch_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        logger.info(f"\nUpdate completed at: {end_time}")
        logger.info(f"Total time: {total_time:.2f} seconds")
        logger.info(f"Total accounts processed: {total_processed}")
        logger.info(f"  - Updated: {updated_count}")
        logger.info(f"  - Skipped: {skipped_count}")
        logger.info(f"Average processing rate: {avg_rate:.2f} accounts/second")
        logger.info(f"Average batch processing time: {avg_batch_time:.2f} seconds")
        logger.info(f"Total errors encountered: {error_count}")
        
        # Log final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_change = final_memory - initial_memory
        logger.info(f"Final memory usage: {final_memory:.2f} MB")
        logger.info(f"Total memory change: {total_memory_change:+.2f} MB")
        
    except Exception as e:
        logger.error(f"Update failed: {str(e)}")
        raise

if __name__ == "__main__":
    update_all_accounts() 