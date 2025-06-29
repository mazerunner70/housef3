#!/usr/bin/env python3
"""
Script to trigger analytics processing for existing users with transaction data.

This script identifies users who have transaction data but no analytics processing 
status records, and creates the necessary status records to trigger analytics computation.

Usage:
    python trigger_analytics_for_existing_data.py [--user-id USER_ID] [--dry-run]
"""

import sys
import os
import argparse
import logging
from datetime import date, datetime
from typing import Set, List
import boto3
from boto3.dynamodb.conditions import Key, Attr

# Add the backend source to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# AWS Configuration
AWS_REGION = 'eu-west-2'
ENVIRONMENT = 'dev'
PROJECT_NAME = 'housef3'

# Set environment variables that db_utils expects
os.environ['ANALYTICS_DATA_TABLE'] = f'{PROJECT_NAME}-{ENVIRONMENT}-analytics-data'
os.environ['ANALYTICS_STATUS_TABLE'] = f'{PROJECT_NAME}-{ENVIRONMENT}-analytics-status'
os.environ['TRANSACTIONS_TABLE'] = f'{PROJECT_NAME}-{ENVIRONMENT}-transactions'
os.environ['ACCOUNTS_TABLE'] = f'{PROJECT_NAME}-{ENVIRONMENT}-accounts'
os.environ['FILES_TABLE'] = f'{PROJECT_NAME}-{ENVIRONMENT}-transaction-files'

from models.analytics import AnalyticType, AnalyticsProcessingStatus
from utils.db_utils import store_analytics_status

def get_table_names():
    """Get DynamoDB table names for the environment."""
    return {
        'transactions': f'{PROJECT_NAME}-{ENVIRONMENT}-transactions',
        'analytics_status': f'{PROJECT_NAME}-{ENVIRONMENT}-analytics-status',
        'accounts': f'{PROJECT_NAME}-{ENVIRONMENT}-accounts',
        'files': f'{PROJECT_NAME}-{ENVIRONMENT}-transaction-files'
    }

def get_users_with_transaction_data() -> Set[str]:
    """Get all users who have transaction data."""
    logger.info("🔍 Finding users with transaction data...")
    
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    table_names = get_table_names()
    
    # Get users from transactions table
    transactions_table = dynamodb.Table(table_names['transactions'])
    users_with_transactions = set()
    
    try:
        # Scan the transactions table to get all unique user IDs
        paginator = transactions_table.meta.client.get_paginator('scan')
        
        for page in paginator.paginate(
            TableName=table_names['transactions'],
            ProjectionExpression='userId',
            FilterExpression=Attr('userId').exists()
        ):
            for item in page.get('Items', []):
                if 'userId' in item:
                    users_with_transactions.add(item['userId'])
        
        logger.info(f"📊 Found {len(users_with_transactions)} users with transaction data")
        return users_with_transactions
        
    except Exception as e:
        logger.error(f"❌ Error scanning transactions table: {str(e)}")
        return set()

def get_users_with_analytics_status() -> Set[str]:
    """Get all users who already have analytics status records."""
    logger.info("🔍 Finding users with existing analytics status...")
    
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    table_names = get_table_names()
    
    analytics_status_table = dynamodb.Table(table_names['analytics_status'])
    users_with_status = set()
    
    try:
        # Scan the analytics status table to get all unique user IDs
        paginator = analytics_status_table.meta.client.get_paginator('scan')
        
        for page in paginator.paginate(
            TableName=table_names['analytics_status'],
            ProjectionExpression='pk',
            FilterExpression=Attr('pk').exists()
        ):
            for item in page.get('Items', []):
                if 'pk' in item:
                    # pk format is user_id, so extract the user ID
                    users_with_status.add(item['pk'])
        
        logger.info(f"📈 Found {len(users_with_status)} users with analytics status records")
        return users_with_status
        
    except Exception as e:
        logger.error(f"❌ Error scanning analytics status table: {str(e)}")
        return set()

def create_analytics_status_for_user(user_id: str, dry_run: bool = False) -> bool:
    """Create analytics status records for a specific user."""
    logger.info(f"🔄 Creating analytics status records for user: {user_id}")
    
    if dry_run:
        logger.info(f"🧪 DRY RUN: Would create analytics status for user {user_id}")
        return True
    
    success_count = 0
    total_count = len(AnalyticType)
    
    for analytic_type in AnalyticType:
        try:
            status_record = AnalyticsProcessingStatus(
                userId=user_id,
                analyticType=analytic_type,
                lastComputedDate=date(1970, 1, 1),  # Epoch date to indicate never computed
                dataAvailableThrough=date.today(),  # Data is available through today
                computationNeeded=True,
                processingPriority=2  # Medium priority for bulk processing
            )
            
            store_analytics_status(status_record)
            success_count += 1
            
        except Exception as e:
            logger.error(f"❌ Failed to create status for {analytic_type.value}: {str(e)}")
    
    logger.info(f"✅ Created {success_count}/{total_count} analytics status records for user {user_id}")
    return success_count > 0

def main():
    """Main function to trigger analytics for existing data."""
    parser = argparse.ArgumentParser(
        description='Trigger analytics processing for existing users with transaction data'
    )
    parser.add_argument(
        '--user-id', 
        type=str, 
        help='Specific user ID to process (if not provided, processes all users)'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true', 
        help='Show what would be done without actually creating records'
    )
    parser.add_argument(
        '--force', 
        action='store_true', 
        help='Force creation even for users who already have analytics status'
    )
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting analytics trigger for existing data")
    logger.info(f"🏷️  Environment: {ENVIRONMENT}")
    logger.info(f"🧪 Dry run: {args.dry_run}")
    
    try:
        if args.user_id:
            # Process specific user
            logger.info(f"🎯 Processing specific user: {args.user_id}")
            success = create_analytics_status_for_user(args.user_id, args.dry_run)
            if success:
                logger.info(f"✅ Successfully triggered analytics for user {args.user_id}")
            else:
                logger.error(f"❌ Failed to trigger analytics for user {args.user_id}")
        else:
            # Process all users
            users_with_data = get_users_with_transaction_data()
            if not users_with_data:
                logger.info("📭 No users with transaction data found")
                return
            
            users_with_status = get_users_with_analytics_status() if not args.force else set()
            users_to_process = users_with_data - users_with_status
            
            if not users_to_process:
                logger.info("✅ All users with transaction data already have analytics status records")
                return
            
            logger.info(f"🎯 Found {len(users_to_process)} users needing analytics processing")
            
            success_count = 0
            for user_id in users_to_process:
                if create_analytics_status_for_user(user_id, args.dry_run):
                    success_count += 1
            
            logger.info(f"✅ Successfully triggered analytics for {success_count}/{len(users_to_process)} users")
        
        if not args.dry_run:
            logger.info("🔄 Analytics processor will pick up these status records within 10 minutes")
            logger.info("📊 You can monitor progress with: ./scripts/analytics_diagnostics.sh logs")
        
    except Exception as e:
        logger.error(f"❌ Script failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 