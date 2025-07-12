#!/usr/bin/env python3
import os
import sys
import boto3
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any
from typing_extensions import Self

# Add the backend source directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend/src'))

from models.transaction import Transaction

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
TRANSACTIONS_TABLE = os.environ.get('TRANSACTIONS_TABLE', f'housef3-{ENVIRONMENT}-transactions')

def get_dynamodb_client():
    """Get the DynamoDB client."""
    return boto3.client('dynamodb')

def get_dynamodb_resource():
    """Get the DynamoDB resource."""
    return boto3.resource('dynamodb')

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
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(TRANSACTIONS_TABLE)
        
        logger.info("Starting transaction migration...")
        
        # Track statistics
        total_processed = 0
        total_batches = 0
        error_count = 0
        status_counts = {}
        
        # Scan the table with pagination
        scan_kwargs = {
            'Select': 'ALL_ATTRIBUTES'
        }
        
        while True:
            response = table.scan(**scan_kwargs)
            items = response.get('Items', [])
            
            if not items:
                break
                
            # Process items in smaller batches (25 items per batch for DynamoDB limits)
            for i in range(0, len(items), 25):
                batch = items[i:i+25]
                try:
                    # Count statuses before update
                    for item in batch:
                        status = item.get('status', 'None')
                        status_counts[status] = status_counts.get(status, 0) + 1
                    
                    update_transaction_batch(table, batch)
                    total_batches += 1
                    total_processed += len(batch)
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error processing batch {total_batches + 1}: {str(e)}")
                    continue
                
                logger.info(f"Processed batch {total_batches} ({total_processed} transactions total)")
            
            # Check if we need to paginate
            if 'LastEvaluatedKey' in response:
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            else:
                break
        
        logger.info(f"Migration completed!")
        logger.info(f"Total transactions processed: {total_processed}")
        logger.info(f"Total batches processed: {total_batches}")
        logger.info(f"Total errors encountered: {error_count}")
        logger.info("Status distribution:")
        for status, count in status_counts.items():
            logger.info(f"  {status}: {count}")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    migrate_transactions() 