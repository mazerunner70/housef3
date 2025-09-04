#!/usr/bin/env python3
"""
Migration script to populate importsStartDate and importsEndDate fields
from existing firstTransactionDate and lastTransactionDate values.

This script scans all accounts in the database and updates the new imports date
fields with the values from the existing transaction date fields.
"""

import os
import sys
import logging
import boto3
from typing import List
from botocore.exceptions import ClientError
from pydantic import ValidationError

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.account import Account
from utils.db_utils import get_accounts_table, update_account

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def scan_all_accounts() -> List[Account]:
    """
    Scan all accounts from the database.
    
    Returns:
        List of all Account objects in the database
    """
    accounts = []
    try:
        # Use paginated scan to handle large datasets
        table = get_accounts_table()
        response = table.scan()
        
        while True:
            for item in response.get('Items', []):
                account_id = item.get('accountId', 'unknown')
                try:
                    account = Account.from_dynamodb_item(item)
                    accounts.append(account)
                except (ValueError, ValidationError) as e:
                    # Handle expected validation/conversion errors - these are data quality issues
                    logger.exception(f"Validation error deserializing account {account_id}: {e}")
                    continue
                except Exception as e:
                    # Handle unexpected errors - these indicate potential code bugs or infrastructure issues
                    logger.exception(f"Unexpected error deserializing account {account_id}: {e}")
                    # Re-raise to surface fatal issues that need investigation
                    raise
            
            # Check if there are more pages
            if 'LastEvaluatedKey' not in response:
                break
                
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        
        logger.info(f"Found {len(accounts)} accounts total")
        return accounts
        
    except ClientError as e:
        logger.error(f"Error scanning accounts table: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error scanning accounts: {e}")
        raise

def update_account_imports_dates(account: Account) -> bool:
    """
    Update an account's imports dates from its transaction dates.
    
    Args:
        account: The Account object to update
        
    Returns:
        True if the account was updated, False if no update was needed
    """
    # Check if imports dates are already set
    if account.imports_start_date is not None and account.imports_end_date is not None:
        logger.debug(f"Account {account.account_id} already has imports dates set")
        return False
    
    # Check if we have transaction dates to copy from
    if account.first_transaction_date is None and account.last_transaction_date is None:
        logger.debug(f"Account {account.account_id} has no transaction dates to copy")
        return False
    
    # Prepare update data
    update_data = {}
    
    # Set imports start date from first transaction date
    if account.imports_start_date is None and account.first_transaction_date is not None:
        update_data['imports_start_date'] = account.first_transaction_date
        logger.debug(f"Setting importsStartDate to {account.first_transaction_date}")
    
    # Set imports end date from last transaction date  
    if account.imports_end_date is None and account.last_transaction_date is not None:
        update_data['imports_end_date'] = account.last_transaction_date
        logger.debug(f"Setting importsEndDate to {account.last_transaction_date}")
    
    # Update the account if we have changes
    if update_data:
        try:
            updated_account = update_account(account.account_id, account.user_id, update_data)
            logger.info(f"Updated account {account.account_id} ({account.account_name}) - "
                       f"importsStartDate: {updated_account.imports_start_date}, "
                       f"importsEndDate: {updated_account.imports_end_date}")
            return True
        except Exception as e:
            logger.error(f"Error updating account {account.account_id}: {e}")
            return False
    
    return False

def main():
    """Main migration function."""
    logger.info("Starting imports dates migration...")
    
    try:
        # Scan all accounts
        accounts = scan_all_accounts()
        
        if not accounts:
            logger.info("No accounts found to migrate")
            return
        
        # Update each account
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for account in accounts:
            try:
                if update_account_imports_dates(account):
                    updated_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                logger.error(f"Error processing account {account.account_id}: {e}")
                error_count += 1
                continue
        
        # Report results
        logger.info("Migration completed!")
        logger.info(f"Total accounts processed: {len(accounts)}")
        logger.info(f"Accounts updated: {updated_count}")
        logger.info(f"Accounts skipped: {skipped_count}")
        logger.info(f"Accounts with errors: {error_count}")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check environment variables
    required_env_vars = ['ACCOUNTS_TABLE']
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please set the required environment variables before running this script.")
        sys.exit(1)
    
    main()
