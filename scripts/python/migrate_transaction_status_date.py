#!/usr/bin/env python3
import os
import sys
import boto3
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
from typing_extensions import Self
from botocore.exceptions import ClientError, ConnectionError

# Add the backend source directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend/src'))

from models.transaction import Transaction

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'housef3')
TRANSACTIONS_TABLE = os.environ.get('TRANSACTIONS_TABLE', f'{PROJECT_NAME}-{ENVIRONMENT}-transactions')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

def check_table_exists(table_name: str) -> bool:
    """
    Check if the DynamoDB table exists and is active.
    """
    try:
        dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)
        response = dynamodb.describe_table(TableName=table_name)
        table_status = response['Table']['TableStatus']
        logger.info(f"Table {table_name} status: {table_status}")
        return table_status == 'ACTIVE'
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'ResourceNotFoundException':
            logger.error(f"Table {table_name} does not exist")
            return False
        logger.error(f"Error checking table {table_name}: {str(e)}")
        raise

def get_table_info(table_name: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about the DynamoDB table.
    """
    try:
        dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)
        response = dynamodb.describe_table(TableName=table_name)
        table_info = response['Table']
        logger.info(f"Table {table_name} info:")
        logger.info(f"  - Item count: {table_info.get('ItemCount', 'N/A')}")
        logger.info(f"  - Size (bytes): {table_info.get('TableSizeBytes', 'N/A')}")
        logger.info(f"  - Status: {table_info.get('TableStatus', 'N/A')}")
        return table_info
    except ClientError as e:
        logger.error(f"Error getting table info for {table_name}: {str(e)}")
        return None

def get_dynamodb_client():
    """Get the DynamoDB client with connection diagnostics."""
    try:
        client = boto3.client('dynamodb', region_name=AWS_REGION)
        # Test the connection
        client.list_tables(Limit=1)
        logger.info("Successfully connected to DynamoDB")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to DynamoDB: {str(e)}")
        raise

def get_dynamodb_resource():
    """Get the DynamoDB resource with connection diagnostics."""
    try:
        resource = boto3.resource('dynamodb', region_name=AWS_REGION)
        # Verify we can access the table
        table = resource.Table(TRANSACTIONS_TABLE)
        table.table_status  # This will raise an exception if the table doesn't exist
        logger.info(f"Successfully connected to DynamoDB and verified table {TRANSACTIONS_TABLE}")
        return resource
    except Exception as e:
        logger.error(f"Failed to initialize DynamoDB resource: {str(e)}")
        raise

def initialize_dynamodb() -> bool:
    """
    Initialize DynamoDB connection and verify table access.
    Returns True if initialization is successful.
    """
    try:
        logger.info("Initializing DynamoDB connection...")
        
        # Check AWS credentials
        session = boto3.Session()
        credentials = session.get_credentials()
        if not credentials:
            logger.error("No AWS credentials found")
            return False
            
        # Log configuration
        logger.info(f"Using AWS Region: {AWS_REGION}")
        logger.info(f"Using table: {TRANSACTIONS_TABLE}")
        
        # Check if table exists and is accessible
        if not check_table_exists(TRANSACTIONS_TABLE):
            return False
            
        # Get table information
        table_info = get_table_info(TRANSACTIONS_TABLE)
        if not table_info:
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize DynamoDB: {str(e)}")
        return False

def update_transaction_batch(table, items: list[Dict[str, Any]]) -> None:
    """
    Update a batch of transactions with their computed status_date field.
    """
    with table.batch_writer() as batch:
        for item in items:
            try:
                # Log the raw item for debugging
                logger.debug(f"Processing item: {item}")
                
                # Create a Transaction object to compute the status_date
                transaction = Transaction.from_dynamodb_item(item)
                
                # The status_date will be computed automatically in to_dynamodb_item()
                # based on the existing status and date fields
                update_item = transaction.to_dynamodb_item()
                
                batch.put_item(Item=update_item)
                logger.debug(f"Updated transaction {item.get('transactionId', 'unknown')} with status {transaction.status}")
            except Exception as e:
                logger.error(f"Error updating transaction {item.get('transactionId', 'unknown')}: {str(e)}")
                # Log more details about the error and item
                logger.error(f"Error details: {str(e)}")
                logger.error(f"Problematic item: {item}")

def migrate_transactions():
    """
    Main migration function to update all transactions with the status_date field.
    """
    try:
        # Initialize DynamoDB and verify connection
        if not initialize_dynamodb():
            logger.error("Failed to initialize DynamoDB connection. Aborting migration.")
            return

        logger.info("Starting transaction migration...")
        
        # Get DynamoDB resource after successful initialization
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(TRANSACTIONS_TABLE)
        
        # Track statistics
        total_processed = 0
        total_batches = 0
        error_count = 0
        status_counts = {}
        batch_processing_times = []
        
        # Track memory usage
        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        logger.info(f"Initial memory usage: {initial_memory:.2f} MB")
        
        # Scan the table with pagination
        scan_kwargs = {
            'Select': 'ALL_ATTRIBUTES'
        }
        
        start_time = datetime.now()
        logger.info(f"Migration started at: {start_time}")
        
        while True:
            batch_start_time = datetime.now()
            
            try:
                response = table.scan(**scan_kwargs)
                items = response.get('Items', [])
                
                if not items:
                    break
                    
                # Log batch details
                logger.info(f"Retrieved batch of {len(items)} items")
                
                # Process items in smaller batches (25 items per batch for DynamoDB limits)
                for i in range(0, len(items), 25):
                    batch = items[i:i+25]
                    try:
                        # Count statuses before update
                        for item in batch:
                            status = item.get('status', 'None')
                            status_counts[status] = status_counts.get(status, 0) + 1
                        
                        # Process the batch
                        batch_process_start = datetime.now()
                        update_transaction_batch(table, batch)
                        batch_process_time = (datetime.now() - batch_process_start).total_seconds()
                        batch_processing_times.append(batch_process_time)
                        
                        total_batches += 1
                        total_processed += len(batch)
                        
                        # Log progress with rate information
                        if total_processed % 100 == 0:
                            elapsed_time = (datetime.now() - start_time).total_seconds()
                            rate = total_processed / elapsed_time if elapsed_time > 0 else 0
                            logger.info(f"Progress: {total_processed} transactions processed at {rate:.2f} items/second")
                            
                            # Log memory usage
                            current_memory = process.memory_info().rss / 1024 / 1024  # MB
                            memory_change = current_memory - initial_memory
                            logger.info(f"Current memory usage: {current_memory:.2f} MB (Change: {memory_change:+.2f} MB)")
                            
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error processing batch {total_batches + 1}: {str(e)}")
                        continue
                    
                    # Log batch completion
                    logger.info(f"Completed batch {total_batches} ({total_processed} transactions total)")
                
                # Calculate and log batch processing time
                batch_time = (datetime.now() - batch_start_time).total_seconds()
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
        avg_batch_time = sum(batch_processing_times) / len(batch_processing_times) if batch_processing_times else 0
        
        logger.info(f"\nMigration completed at: {end_time}")
        logger.info(f"Total time: {total_time:.2f} seconds")
        logger.info(f"Total transactions processed: {total_processed}")
        logger.info(f"Total batches processed: {total_batches}")
        logger.info(f"Average processing rate: {avg_rate:.2f} items/second")
        logger.info(f"Average batch processing time: {avg_batch_time:.2f} seconds")
        logger.info(f"Total errors encountered: {error_count}")
        logger.info("Status distribution:")
        for status, count in status_counts.items():
            logger.info(f"  {status}: {count}")
        
        # Log final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_change = final_memory - initial_memory
        logger.info(f"Final memory usage: {final_memory:.2f} MB")
        logger.info(f"Total memory change: {total_memory_change:+.2f} MB")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    migrate_transactions() 