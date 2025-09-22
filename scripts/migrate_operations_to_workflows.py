#!/usr/bin/env python3
"""
Migration script to copy data from housef3-dev-operations table to housef3-dev-workflows table.

This script:
1. Scans all items from the operations table
2. Copies them to the workflows table with identical structure
3. Provides progress reporting and error handling
4. Supports dry-run mode for testing

Usage:
    python3 migrate_operations_to_workflows.py --environment dev [--dry-run] [--batch-size 25]
"""

import argparse
import boto3
import logging
import sys
from typing import Dict, Any, List
from botocore.exceptions import ClientError
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OperationsMigrator:
    """Handles migration from operations table to workflows table"""
    
    def __init__(self, environment: str, dry_run: bool = False):
        self.environment = environment
        self.dry_run = dry_run
        self.dynamodb = boto3.resource('dynamodb')
        
        # Table names
        self.source_table_name = f"housef3-{environment}-operations"
        self.target_table_name = f"housef3-{environment}-workflows"
        
        # Initialize tables
        try:
            self.source_table = self.dynamodb.Table(self.source_table_name)
            self.target_table = self.dynamodb.Table(self.target_table_name)
            
            # Verify tables exist
            self.source_table.load()
            self.target_table.load()
            
            logger.info(f"Source table: {self.source_table_name}")
            logger.info(f"Target table: {self.target_table_name}")
            logger.info(f"Dry run mode: {self.dry_run}")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.error(f"Table not found: {e.response['Error']['Message']}")
                sys.exit(1)
            else:
                raise
    
    def get_source_item_count(self) -> int:
        """Get approximate count of items in source table"""
        try:
            response = self.source_table.describe_table()
            return response['Table']['ItemCount']
        except ClientError as e:
            logger.warning(f"Could not get item count: {e}")
            return 0
    
    def scan_source_table(self, batch_size: int = 25) -> List[Dict[str, Any]]:
        """Scan all items from source table in batches"""
        items = []
        last_evaluated_key = None
        
        while True:
            scan_kwargs = {
                'Limit': batch_size
            }
            
            if last_evaluated_key:
                scan_kwargs['ExclusiveStartKey'] = last_evaluated_key
            
            try:
                response = self.source_table.scan(**scan_kwargs)
                batch_items = response.get('Items', [])
                items.extend(batch_items)
                
                logger.info(f"Scanned {len(batch_items)} items (total: {len(items)})")
                
                last_evaluated_key = response.get('LastEvaluatedKey')
                if not last_evaluated_key:
                    break
                    
            except ClientError as e:
                logger.error(f"Error scanning source table: {e}")
                raise
        
        return items
    
    def migrate_batch(self, items: List[Dict[str, Any]]) -> tuple[int, int]:
        """Migrate a batch of items to target table"""
        success_count = 0
        error_count = 0
        
        if self.dry_run:
            logger.info(f"DRY RUN: Would migrate {len(items)} items")
            return len(items), 0
        
        try:
            with self.target_table.batch_writer() as batch:
                for item in items:
                    try:
                        # Copy item as-is (structure is identical)
                        batch.put_item(Item=item)
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Error migrating item {item.get('operationId', 'unknown')}: {e}")
                        error_count += 1
                        
        except ClientError as e:
            logger.error(f"Batch write error: {e}")
            error_count = len(items)
        
        return success_count, error_count
    
    def verify_migration(self, source_items: List[Dict[str, Any]]) -> bool:
        """Verify that all items were migrated correctly"""
        if self.dry_run:
            logger.info("DRY RUN: Skipping verification")
            return True
        
        logger.info("Verifying migration...")
        verification_errors = 0
        
        for item in source_items:
            operation_id = item.get('operationId')
            if not operation_id:
                continue
            
            try:
                response = self.target_table.get_item(
                    Key={'operationId': operation_id}
                )
                
                if 'Item' not in response:
                    logger.error(f"Missing item in target table: {operation_id}")
                    verification_errors += 1
                else:
                    target_item = response['Item']
                    # Compare key fields
                    if (target_item.get('userId') != item.get('userId') or
                        target_item.get('operationType') != item.get('operationType') or
                        target_item.get('status') != item.get('status')):
                        logger.error(f"Data mismatch for item: {operation_id}")
                        verification_errors += 1
                        
            except ClientError as e:
                logger.error(f"Error verifying item {operation_id}: {e}")
                verification_errors += 1
        
        if verification_errors == 0:
            logger.info("✅ Migration verification successful")
            return True
        else:
            logger.error(f"❌ Migration verification failed: {verification_errors} errors")
            return False
    
    def run_migration(self, batch_size: int = 25) -> bool:
        """Run the complete migration process"""
        start_time = datetime.now()
        
        logger.info("=" * 60)
        logger.info("STARTING OPERATIONS TO WORKFLOWS TABLE MIGRATION")
        logger.info("=" * 60)
        
        # Get source item count
        estimated_count = self.get_source_item_count()
        if estimated_count > 0:
            logger.info(f"Estimated items to migrate: {estimated_count}")
        
        # Scan source table
        logger.info("Scanning source table...")
        try:
            source_items = self.scan_source_table(batch_size)
            logger.info(f"Found {len(source_items)} items to migrate")
            
            if len(source_items) == 0:
                logger.info("No items to migrate")
                return True
                
        except Exception as e:
            logger.error(f"Failed to scan source table: {e}")
            return False
        
        # Migrate in batches
        logger.info("Starting migration...")
        total_success = 0
        total_errors = 0
        
        # Process in batches of 25 (DynamoDB batch write limit)
        for i in range(0, len(source_items), batch_size):
            batch = source_items[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(source_items) + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)")
            
            success, errors = self.migrate_batch(batch)
            total_success += success
            total_errors += errors
            
            if errors > 0:
                logger.warning(f"Batch {batch_num} had {errors} errors")
        
        # Verify migration
        if total_errors == 0:
            verification_success = self.verify_migration(source_items)
        else:
            verification_success = False
        
        # Summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info("=" * 60)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total items processed: {len(source_items)}")
        logger.info(f"Successfully migrated: {total_success}")
        logger.info(f"Errors: {total_errors}")
        logger.info(f"Duration: {duration}")
        logger.info(f"Verification: {'✅ PASSED' if verification_success else '❌ FAILED'}")
        
        if self.dry_run:
            logger.info("🔍 DRY RUN COMPLETED - No actual data was migrated")
        elif total_errors == 0 and verification_success:
            logger.info("✅ MIGRATION COMPLETED SUCCESSFULLY")
        else:
            logger.error("❌ MIGRATION COMPLETED WITH ERRORS")
        
        return total_errors == 0 and verification_success


def main():
    parser = argparse.ArgumentParser(description='Migrate operations table to workflows table')
    parser.add_argument('--environment', '-e', required=True, 
                       help='Environment (dev, staging, prod)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run in dry-run mode (no actual migration)')
    parser.add_argument('--batch-size', type=int, default=25,
                       help='Batch size for processing (default: 25)')
    
    args = parser.parse_args()
    
    # Validate batch size
    if args.batch_size < 1 or args.batch_size > 25:
        logger.error("Batch size must be between 1 and 25")
        sys.exit(1)
    
    try:
        migrator = OperationsMigrator(args.environment, args.dry_run)
        success = migrator.run_migration(args.batch_size)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
