#!/usr/bin/env python3
"""
Migration script to update analytics_status records to use numeric computationNeeded.
This script will:
1. Scan all records in the analytics_status table
2. Convert string 'true'/'false' computationNeeded values to numeric 1/0
3. Update the records in DynamoDB
"""
import boto3
from boto3.dynamodb.types import Binary
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'housef3')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
TABLE_NAME = f"{PROJECT_NAME}-{ENVIRONMENT}-analytics-status"

def get_all_records() -> List[Dict[str, Any]]:
    """Get all records from the analytics_status table."""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)
    
    try:
        logger.info(f"Scanning table {TABLE_NAME}...")
        response = table.scan()
        items = response['Items']
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        
        logger.info(f"Found {len(items)} records")
        return items
    except Exception as e:
        logger.error(f"Error scanning table: {str(e)}")
        raise

def update_record(record: Dict[str, Any]) -> bool:
    """Update a single record with boolean computationNeeded."""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)
    
    try:
        # Convert boolean to DynamoDB Binary type
        binary_true = Binary(b'\x01')  # Binary representation of true
        
        # Update the record to set computationNeeded to true
        response = table.update_item(
            Key={
                'pk': record['pk'],
                'sk': record['sk']
            },
            UpdateExpression='SET computationNeeded = :val, lastUpdated = :now',
            ExpressionAttributeValues={
                ':val': binary_true,  # Use Binary type for boolean
                ':now': datetime.now(timezone.utc).isoformat()
            }
        )
        
        logger.info(f"Updated record {record['pk']}#{record['sk']}: computationNeeded -> True (Binary)")
        return True
    except Exception as e:
        logger.error(f"Error updating record {record.get('pk', 'unknown')}#{record.get('sk', 'unknown')}: {str(e)}")
        return False

def main():
    """Main migration function."""
    try:
        logger.info("Starting analytics_status update...")
        
        # Get all records
        records = get_all_records()
        
        # Track statistics
        stats = {
            'total': len(records),
            'updated': 0,
            'skipped': 0,
            'failed': 0
        }
        
        # Process each record
        for record in records:
            try:
                if update_record(record):
                    stats['updated'] += 1
                else:
                    stats['failed'] += 1
            except Exception as e:
                logger.error(f"Failed to process record: {str(e)}")
                stats['failed'] += 1
        
        # Log final statistics
        logger.info("\nMigration completed:")
        logger.info(f"Total records: {stats['total']}")
        logger.info(f"Updated: {stats['updated']}")
        logger.info(f"Skipped: {stats['skipped']}")
        logger.info(f"Failed: {stats['failed']}")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    main() 