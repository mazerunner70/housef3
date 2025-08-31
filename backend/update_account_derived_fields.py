#!/usr/bin/env python3
"""
Script to update derived transaction date fields for all accounts.

This script scans all accounts in the system and updates their first_transaction_date 
and last_transaction_date fields by analyzing their actual transactions. This is required
for the get_account_date_range_for_transfers function to work properly.

Usage:
    python3 update_account_derived_fields.py [--dry-run] [--user-id USER_ID]
    
Options:
    --dry-run    Show what would be updated without making changes
    --user-id    Only update accounts for a specific user ID
"""

import sys
import os
import argparse
import logging
from typing import List, Dict, Any, Optional

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up environment variables for DynamoDB tables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
PROJECT_NAME = 'housef3'

# Set default table names if not already set
os.environ.setdefault('ACCOUNTS_TABLE', f'{PROJECT_NAME}-{ENVIRONMENT}-accounts')
os.environ.setdefault('TRANSACTIONS_TABLE', f'{PROJECT_NAME}-{ENVIRONMENT}-transactions')
os.environ.setdefault('FILES_TABLE', f'{PROJECT_NAME}-{ENVIRONMENT}-transaction-files')
os.environ.setdefault('FILE_MAPS_TABLE', f'{PROJECT_NAME}-{ENVIRONMENT}-file-maps')
os.environ.setdefault('CATEGORIES_TABLE_NAME', f'{PROJECT_NAME}-{ENVIRONMENT}-categories')
os.environ.setdefault('USER_PREFERENCES_TABLE', f'{PROJECT_NAME}-{ENVIRONMENT}-user-preferences')

from utils.db_utils import (
    get_accounts_table, 
    update_account_derived_values, 
    get_account_transaction_date_range,
    list_user_accounts
)
from models.account import Account

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def scan_all_accounts() -> List[Dict[str, Any]]:
    """
    Scan all accounts in the DynamoDB table.
    
    Returns:
        List of account items from DynamoDB
    """
    logger.info("Scanning all accounts from DynamoDB...")
    
    accounts_table = get_accounts_table()
    all_accounts = []
    
    try:
        # Use scan to get all accounts
        response = accounts_table.scan()
        all_accounts.extend(response.get('Items', []))
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            logger.info(f"Continuing scan... Found {len(all_accounts)} accounts so far")
            response = accounts_table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            all_accounts.extend(response.get('Items', []))
        
        logger.info(f"Found {len(all_accounts)} total accounts")
        return all_accounts
        
    except Exception as e:
        logger.error(f"Error scanning accounts: {str(e)}")
        raise


def get_accounts_for_user(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all accounts for a specific user.
    
    Args:
        user_id: The user ID to filter by
        
    Returns:
        List of account items for the user
    """
    logger.info(f"Getting accounts for user: {user_id}")
    
    try:
        accounts = list_user_accounts(user_id)
        # Convert Account objects back to dict format for consistency
        account_items = []
        for account in accounts:
            account_items.append(account.to_dynamodb_item())
        
        logger.info(f"Found {len(account_items)} accounts for user {user_id}")
        return account_items
        
    except Exception as e:
        logger.error(f"Error getting accounts for user {user_id}: {str(e)}")
        raise


def check_account_needs_update(account_item: Dict[str, Any]) -> bool:
    """
    Check if an account needs its derived fields updated.
    
    Args:
        account_item: Account item from DynamoDB
        
    Returns:
        True if the account needs updating, False otherwise
    """
    account_id = account_item.get('accountId')
    # Use the correct DynamoDB field names (camelCase)
    first_date = account_item.get('firstTransactionDate')
    last_date = account_item.get('lastTransactionDate')
    
    # Account needs update if either date field is missing
    needs_update = first_date is None or last_date is None
    
    if needs_update:
        logger.debug(f"Account {account_id} needs update: first_date={first_date}, last_date={last_date}")
    else:
        logger.debug(f"Account {account_id} already has derived fields populated: first_date={first_date}, last_date={last_date}")
    
    return needs_update


def update_account_derived_fields(account_item: Dict[str, Any], dry_run: bool = False) -> bool:
    """
    Update derived fields for a single account.
    
    Args:
        account_item: Account item from DynamoDB
        dry_run: If True, only show what would be updated
        
    Returns:
        True if update was successful (or would be successful in dry-run), False otherwise
    """
    account_id = account_item.get('accountId')
    user_id = account_item.get('userId')
    
    if not account_id or not user_id:
        logger.error(f"Account missing required fields: accountId={account_id}, userId={user_id}")
        return False
    
    try:
        # Get the current transaction date range
        first_date, last_date = get_account_transaction_date_range(account_id)
        
        if dry_run:
            logger.info(f"[DRY RUN] Would update account {account_id}: first_date={first_date}, last_date={last_date}")
            return True
        else:
            # Actually update the account
            success = update_account_derived_values(account_id, user_id)
            if success:
                logger.info(f"Updated account {account_id}: first_date={first_date}, last_date={last_date}")
            else:
                logger.error(f"Failed to update account {account_id}")
            return success
            
    except Exception as e:
        logger.error(f"Error updating account {account_id}: {str(e)}")
        return False


def main():
    """Main function to update derived fields for all accounts."""
    parser = argparse.ArgumentParser(description='Update derived transaction date fields for accounts')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be updated without making changes')
    parser.add_argument('--user-id', type=str, 
                       help='Only update accounts for a specific user ID')
    
    args = parser.parse_args()
    
    logger.info("Starting account derived fields update script")
    if args.dry_run:
        logger.info("Running in DRY RUN mode - no changes will be made")
    
    try:
        # Get accounts to process
        if args.user_id:
            account_items = get_accounts_for_user(args.user_id)
        else:
            account_items = scan_all_accounts()
        
        if not account_items:
            logger.info("No accounts found to process")
            return
        
        # Filter accounts that need updating
        accounts_to_update = []
        for account_item in account_items:
            account_id = account_item.get('accountId')
            # Use the correct DynamoDB field names (camelCase)
            first_date = account_item.get('firstTransactionDate')
            last_date = account_item.get('lastTransactionDate')
            logger.debug(f"Account {account_id}: firstTransactionDate={first_date}, lastTransactionDate={last_date}")
            if check_account_needs_update(account_item):
                accounts_to_update.append(account_item)
        
        logger.info(f"Found {len(accounts_to_update)} accounts that need derived field updates")
        
        if not accounts_to_update:
            logger.info("All accounts already have derived fields populated")
            return
        
        # Update accounts
        successful_updates = 0
        failed_updates = 0
        
        for i, account_item in enumerate(accounts_to_update, 1):
            account_id = account_item.get('accountId')
            logger.info(f"Processing account {i}/{len(accounts_to_update)}: {account_id}")
            
            if update_account_derived_fields(account_item, args.dry_run):
                successful_updates += 1
            else:
                failed_updates += 1
        
        # Summary
        logger.info("=" * 50)
        logger.info("UPDATE SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total accounts processed: {len(accounts_to_update)}")
        logger.info(f"Successful updates: {successful_updates}")
        logger.info(f"Failed updates: {failed_updates}")
        
        if args.dry_run:
            logger.info("This was a DRY RUN - no actual changes were made")
        
        if failed_updates > 0:
            logger.warning(f"{failed_updates} accounts failed to update - check logs for details")
            sys.exit(1)
        else:
            logger.info("All accounts updated successfully!")
            
    except Exception as e:
        logger.error(f"Script failed with error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
