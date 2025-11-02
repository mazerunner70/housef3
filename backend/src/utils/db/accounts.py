"""
Account database operations.

This module provides CRUD operations for accounts.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union, Tuple
from boto3.dynamodb.conditions import Key

from models import Account, AccountUpdate
from .base import (
    tables,
    dynamodb_operation,
    retry_on_throttle,
    monitor_performance,
    cache_result,
    NotFound,
    check_user_owns_resource,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def checked_mandatory_account(account_id: Optional[uuid.UUID], user_id: str) -> Account:
    """
    Check if account exists and user has access to it.
    
    Args:
        account_id: ID of the account
        user_id: ID of the user requesting access
        
    Returns:
        Account object if found and authorized
        
    Raises:
        NotFound: If account_id is None or account doesn't exist
        NotAuthorized: If user doesn't own the account
    """
    if not account_id:
        raise NotFound("Account ID is required")
    account = get_account(account_id)
    if not account:
        raise NotFound("Account not found")
    check_user_owns_resource(account.user_id, user_id)
    return account


def checked_optional_account(account_id: Optional[uuid.UUID], user_id: str) -> Optional[Account]:
    """
    Check if account exists and user has access to it, allowing None.
    
    Args:
        account_id: ID of the account (or None)
        user_id: ID of the user requesting access
        
    Returns:
        Account object if found and authorized, None if account_id is None or not found
    """
    if not account_id:
        return None
    account = get_account(account_id)
    if not account:
        return None
    check_user_owns_resource(account.user_id, user_id)
    return account


# ============================================================================
# CRUD Operations
# ============================================================================

@cache_result(ttl_seconds=60, maxsize=100)
@monitor_performance(warn_threshold_ms=200)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("get_account")
def get_account(account_id: uuid.UUID) -> Optional[Account]:
    """
    Retrieve an account by ID.
    
    Args:
        account_id: The unique identifier of the account
        
    Returns:
        Account object if found, None otherwise
    """
    response = tables.accounts.get_item(Key={'accountId': str(account_id)})

    if 'Item' in response:
        return Account.from_dynamodb_item(response['Item'])
    return None


@monitor_performance(operation_type="query", warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("list_user_accounts")
def list_user_accounts(user_id: str) -> List[Account]:
    """
    List all accounts for a specific user.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        List of Account objects
    """
    # Query using GSI for userId
    response = tables.accounts.query(
        IndexName='UserIdIndex',
        KeyConditionExpression=Key('userId').eq(user_id)
    )
    
    accounts = []
    for item in response.get('Items', []):
        # Check and fix balance format if needed
        try:
            account = Account.from_dynamodb_item(item)
            accounts.append(account)
        except Exception as e:
            logger.error(f"Error creating Account from item: {str(e)}")
            logger.error(f"Problematic item: {item}")
            raise
    logger.info(f"Listed {len(accounts)} accounts for user {user_id}")    
    return accounts


@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("create_account")
def create_account(account: Account):
    """
    Create a new account.
    
    Args:
        account: Account object to create
    """
    # Save to DynamoDB
    tables.accounts.put_item(Item=account.to_dynamodb_item())


@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("update_account")
def update_account(account_id: uuid.UUID, user_id: str, update_data: Dict[str, Any]) -> Account:
    """
    Update an existing account.
    
    Args:
        account_id: The unique identifier of the account to update
        user_id: The ID of the user making the request
        update_data: Dictionary containing fields to update
        
    Returns:
        Updated Account object
    """
    # Retrieve the existing account
    account = checked_mandatory_account(account_id, user_id)
    
    # Create an AccountUpdate DTO from the update_data
    account_update_dto = AccountUpdate(**update_data)
    
    # Use the model's method to update details
    account.update_account_details(account_update_dto)
    
    # Save updates to DynamoDB
    tables.accounts.put_item(Item=account.to_dynamodb_item())
    
    return account


@monitor_performance(warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("delete_account")
def delete_account(account_id: uuid.UUID, user_id: str) -> bool:
    """
    Delete an account and handle any associated files.
    
    Args:
        account_id: The unique identifier of the account to delete
        user_id: The ID of the user making the request
        
    Returns:
        True if deleted successfully
    """
    # Import here to avoid circular dependency
    from .files import list_account_files, delete_transaction_file
    
    # Check if the account exists and user has access
    _ = checked_mandatory_account(account_id, user_id)
    
    # Get all files associated with this account
    associated_files = list_account_files(account_id)
    logger.info(f"Found {len(associated_files)} files associated with account {str(account_id)}")
    
    # Delete each associated file and its transactions
    for file_item in associated_files:
        # Ensure user owns the file before deleting
        if file_item.user_id != user_id:
            logger.warning(f"Skipping deletion of file {str(file_item.file_id)} as it's not owned by user {user_id}")
            continue
        try:
            # Delete the file and its transactions
            delete_transaction_file(file_item.file_id, user_id)
            logger.info(f"Deleted file {str(file_item.file_id)} and its transactions")
        except Exception as file_error:
            logger.error(f"Error deleting file {str(file_item.file_id)}: {str(file_error)}")
            # Continue with other files
    
    # Delete the account
    tables.accounts.delete_item(Key={'accountId': str(account_id)})
    logger.info(f"Account {str(account_id)} deleted successfully")
    
    return True


# ============================================================================
# Account-Transaction Relationship Functions
# ============================================================================

def get_account_transaction_date_range(account_id: Union[str, uuid.UUID]) -> Tuple[Optional[int], Optional[int]]:
    """
    Get both the earliest and latest transaction dates for a specific account.
    Only considers transactions with status starting with 'new' (non-duplicates).
    
    Args:
        account_id: The account ID
        
    Returns:
        Tuple of (first_date, last_date) as milliseconds since epoch, or (None, None) if no transactions found
    """
    # Import here to avoid circular dependency
    from .transactions import get_first_transaction_date, get_last_transaction_date
    
    try:
        first_date = get_first_transaction_date(account_id)
        last_date = get_last_transaction_date(account_id)
        return (first_date, last_date)
        
    except Exception as e:
        logger.error(f"Error getting transaction date range for account {str(account_id)}: {str(e)}")
        return (None, None)


@monitor_performance(warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("update_account_derived_values")
def update_account_derived_values(account_id: Union[str, uuid.UUID], user_id: str) -> bool:
    """
    Update the derived first_transaction_date and last_transaction_date fields for an account
    by scanning all transactions for that account.
    
    Args:
        account_id: The account ID
        user_id: The user ID (for validation)
        
    Returns:
        True if update was successful, False otherwise
        
    Raises:
        ValueError: If account not found or doesn't belong to user
        Exception: If there's an error updating the account
    """
    # Get the account first to validate it exists and belongs to user
    account_uuid = uuid.UUID(str(account_id)) if isinstance(account_id, str) else account_id
    _ = checked_mandatory_account(account_uuid, user_id)
    
    # Get transaction date range from actual transactions
    first_date, last_date = get_account_transaction_date_range(account_id)
    
    # Update the account directly in DynamoDB using the correct field names
    accounts_table = tables.accounts
    
    # Prepare update expression and values
    update_expression = "SET firstTransactionDate = :first_date, lastTransactionDate = :last_date, updatedAt = :updated_at"
    expression_attribute_values = {
        ':first_date': first_date,
        ':last_date': last_date,
        ':updated_at': int(datetime.now(timezone.utc).timestamp() * 1000)
    }
    
    # Update the item in DynamoDB
    accounts_table.update_item(
        Key={'accountId': str(account_uuid)},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values
    )
    
    logger.info(f"Updated derived values for account {account_id}: first={first_date}, last={last_date}")
    return True

