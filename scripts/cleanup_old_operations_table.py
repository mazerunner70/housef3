#!/usr/bin/env python3
"""
Cleanup script to remove the old operations table after successful migration to workflows table.

This script:
1. Verifies that the workflows table exists and has data
2. Optionally backs up the operations table data to S3
3. Removes the old operations table from Terraform state
4. Provides safety checks and confirmation prompts

Usage:
    python3 cleanup_old_operations_table.py --environment dev [--backup-to-s3] [--force]
"""

import argparse
import boto3
import logging
import sys
import json
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OperationsTableCleanup:
    """Handles cleanup of the old operations table"""
    
    def __init__(self, environment: str, backup_to_s3: bool = False, force: bool = False):
        self.environment = environment
        self.backup_to_s3 = backup_to_s3
        self.force = force
        
        # AWS clients
        self.dynamodb = boto3.resource('dynamodb')
        self.s3 = boto3.client('s3') if backup_to_s3 else None
        
        # Table names
        self.old_table_name = f"housef3-{environment}-operations"
        self.new_table_name = f"housef3-{environment}-workflows"
        self.backup_bucket = f"housef3-{environment}-backups"  # Adjust as needed
        
        logger.info(f"Environment: {environment}")
        logger.info(f"Old table: {self.old_table_name}")
        logger.info(f"New table: {self.new_table_name}")
        logger.info(f"Backup to S3: {backup_to_s3}")
        logger.info(f"Force mode: {force}")
    
    def verify_tables_exist(self) -> tuple[bool, bool]:
        """Verify both tables exist and get their status"""
        old_exists = False
        new_exists = False
        
        try:
            old_table = self.dynamodb.Table(self.old_table_name)
            old_table.load()
            old_exists = True
            logger.info(f"✅ Old table exists: {self.old_table_name}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.info(f"ℹ️  Old table not found: {self.old_table_name}")
            else:
                logger.error(f"Error checking old table: {e}")
                return False, False
        
        try:
            new_table = self.dynamodb.Table(self.new_table_name)
            new_table.load()
            new_exists = True
            logger.info(f"✅ New table exists: {self.new_table_name}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.error(f"❌ New table not found: {self.new_table_name}")
            else:
                logger.error(f"Error checking new table: {e}")
            return False, False
        
        return old_exists, new_exists
    
    def compare_table_counts(self) -> tuple[int, int]:
        """Compare item counts between old and new tables"""
        try:
            old_table = self.dynamodb.Table(self.old_table_name)
            new_table = self.dynamodb.Table(self.new_table_name)
            
            old_response = old_table.describe_table()
            new_response = new_table.describe_table()
            
            old_count = old_response['Table']['ItemCount']
            new_count = new_response['Table']['ItemCount']
            
            logger.info(f"Old table item count: {old_count}")
            logger.info(f"New table item count: {new_count}")
            
            return old_count, new_count
            
        except ClientError as e:
            logger.error(f"Error comparing table counts: {e}")
            return -1, -1
    
    def backup_table_to_s3(self) -> bool:
        """Backup the old table data to S3 before deletion"""
        if not self.backup_to_s3:
            return True
        
        logger.info("Starting S3 backup of old table...")
        
        try:
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_key = f"table-backups/{self.old_table_name}_backup_{timestamp}.json"
            
            # Scan all items from old table
            old_table = self.dynamodb.Table(self.old_table_name)
            items = []
            
            scan_kwargs = {}
            while True:
                response = old_table.scan(**scan_kwargs)
                items.extend(response.get('Items', []))
                
                if 'LastEvaluatedKey' not in response:
                    break
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            
            # Convert Decimal types to float for JSON serialization
            def decimal_default(obj):
                if isinstance(obj, boto3.dynamodb.types.TypeDeserializer().deserialize):
                    return float(obj)
                raise TypeError
            
            # Upload to S3
            backup_data = {
                'table_name': self.old_table_name,
                'backup_timestamp': timestamp,
                'item_count': len(items),
                'items': items
            }
            
            self.s3.put_object(
                Bucket=self.backup_bucket,
                Key=backup_key,
                Body=json.dumps(backup_data, default=str, indent=2),
                ContentType='application/json'
            )
            
            logger.info(f"✅ Backup completed: s3://{self.backup_bucket}/{backup_key}")
            logger.info(f"Backed up {len(items)} items")
            return True
            
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return False
    
    def get_user_confirmation(self) -> bool:
        """Get user confirmation before deleting the table"""
        if self.force:
            logger.info("Force mode enabled - skipping confirmation")
            return True
        
        print("\n" + "="*60)
        print("⚠️  WARNING: DESTRUCTIVE OPERATION")
        print("="*60)
        print(f"You are about to DELETE the table: {self.old_table_name}")
        print("This operation is IRREVERSIBLE!")
        print()
        
        if self.backup_to_s3:
            print("✅ S3 backup will be created before deletion")
        else:
            print("❌ NO BACKUP will be created")
        
        print()
        response = input("Type 'DELETE' to confirm deletion: ")
        
        if response != 'DELETE':
            logger.info("Operation cancelled by user")
            return False
        
        print()
        response = input("Are you absolutely sure? Type 'YES' to proceed: ")
        
        if response != 'YES':
            logger.info("Operation cancelled by user")
            return False
        
        return True
    
    def delete_old_table(self) -> bool:
        """Delete the old operations table"""
        try:
            logger.info(f"Deleting table: {self.old_table_name}")
            
            old_table = self.dynamodb.Table(self.old_table_name)
            old_table.delete()
            
            # Wait for deletion to complete
            logger.info("Waiting for table deletion to complete...")
            old_table.wait_until_not_exists()
            
            logger.info(f"✅ Table deleted successfully: {self.old_table_name}")
            return True
            
        except ClientError as e:
            logger.error(f"❌ Error deleting table: {e}")
            return False
    
    def run_cleanup(self) -> bool:
        """Run the complete cleanup process"""
        logger.info("=" * 60)
        logger.info("STARTING OPERATIONS TABLE CLEANUP")
        logger.info("=" * 60)
        
        # Step 1: Verify tables exist
        old_exists, new_exists = self.verify_tables_exist()
        
        if not old_exists:
            logger.info("✅ Old table doesn't exist - cleanup not needed")
            return True
        
        if not new_exists:
            logger.error("❌ New workflows table doesn't exist - cannot proceed")
            return False
        
        # Step 2: Compare item counts
        old_count, new_count = self.compare_table_counts()
        
        if old_count > 0 and new_count == 0:
            logger.error("❌ Old table has data but new table is empty - migration may not be complete")
            if not self.force:
                return False
        
        if old_count > new_count:
            logger.warning(f"⚠️  Old table has more items ({old_count}) than new table ({new_count})")
            if not self.force:
                logger.error("Use --force to proceed anyway")
                return False
        
        # Step 3: Backup to S3 if requested
        if self.backup_to_s3:
            if not self.backup_table_to_s3():
                logger.error("❌ Backup failed - aborting cleanup")
                return False
        
        # Step 4: Get user confirmation
        if not self.get_user_confirmation():
            return False
        
        # Step 5: Delete the old table
        if not self.delete_old_table():
            return False
        
        logger.info("=" * 60)
        logger.info("✅ CLEANUP COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        logger.info("Next steps:")
        logger.info("1. Update Terraform to remove the old table resource")
        logger.info("2. Run 'terraform plan' to verify the change")
        logger.info("3. Run 'terraform apply' to update the state")
        
        return True


def main():
    parser = argparse.ArgumentParser(description='Cleanup old operations table after migration')
    parser.add_argument('--environment', '-e', required=True,
                       help='Environment (dev, staging, prod)')
    parser.add_argument('--backup-to-s3', action='store_true',
                       help='Backup table data to S3 before deletion')
    parser.add_argument('--force', action='store_true',
                       help='Skip safety checks and confirmations')
    
    args = parser.parse_args()
    
    try:
        cleanup = OperationsTableCleanup(
            environment=args.environment,
            backup_to_s3=args.backup_to_s3,
            force=args.force
        )
        
        success = cleanup.run_cleanup()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("Cleanup cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
