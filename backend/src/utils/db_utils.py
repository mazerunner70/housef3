"""
Utility functions for database operations.
"""
import os
import logging
import traceback
import boto3
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union, Tuple
from botocore.exceptions import ClientError
from decimal import Decimal
import decimal

from pydantic import BaseModel, ValidationError

from models import (
    Account, 
    TransactionFile,
    AccountType,
    Currency,
    AccountCreate,
    AccountUpdate,
    AnalyticsData,
    AnalyticsProcessingStatus,
    AnalyticType,
    ComputationStatus
)
from models.fzip import FZIPJob
from models.category import Category, CategoryType, CategoryUpdate, CategoryRule
from models.transaction import Transaction, TransactionCreate, TransactionUpdate
from models.transaction_file import TransactionFileCreate, TransactionFileUpdate
from boto3.dynamodb.conditions import Key, Attr
from models.file_map import FileMap, FileMapCreate, FileMapUpdate
from utils.transaction_utils import generate_transaction_hash

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')

# Get environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
ACCOUNTS_TABLE = os.environ.get('ACCOUNTS_TABLE')
FILES_TABLE = os.environ.get('FILES_TABLE')
TRANSACTIONS_TABLE = os.environ.get('TRANSACTIONS_TABLE')
FILE_MAPS_TABLE = os.environ.get('FILE_MAPS_TABLE')
CATEGORIES_TABLE_NAME = os.environ.get('CATEGORIES_TABLE_NAME')
ANALYTICS_DATA_TABLE = os.environ.get('ANALYTICS_DATA_TABLE', 'housef3-analytics-data')
ANALYTICS_STATUS_TABLE = os.environ.get('ANALYTICS_STATUS_TABLE', 'housef3-analytics-status')
FZIP_JOBS_TABLE = os.environ.get('FZIP_JOBS_TABLE')

# Initialize table resources lazily
_accounts_table = None
_files_table = None
_transactions_table = None
_file_maps_table = None
_analytics_data_table = None
_analytics_status_table = None
_categories_table = None
_fzip_jobs_table = None

def initialize_tables():
    """Initialize all DynamoDB table resources."""
    global _transactions_table, _accounts_table, _files_table, _file_maps_table
    global _analytics_data_table, _analytics_status_table, _categories_table, _fzip_jobs_table, dynamodb
    
    # Re-initialize DynamoDB resource
    dynamodb = boto3.resource('dynamodb')
    
    # Initialize all tables if their environment variables are set
    if TRANSACTIONS_TABLE:
        _transactions_table = dynamodb.Table(TRANSACTIONS_TABLE)
    if ACCOUNTS_TABLE:
        _accounts_table = dynamodb.Table(ACCOUNTS_TABLE)
    if FILES_TABLE:
        _files_table = dynamodb.Table(FILES_TABLE)
    if FILE_MAPS_TABLE:
        _file_maps_table = dynamodb.Table(FILE_MAPS_TABLE)
    if ANALYTICS_DATA_TABLE:
        _analytics_data_table = dynamodb.Table(ANALYTICS_DATA_TABLE)
    if ANALYTICS_STATUS_TABLE:
        _analytics_status_table = dynamodb.Table(ANALYTICS_STATUS_TABLE)
    if CATEGORIES_TABLE_NAME:
        _categories_table = dynamodb.Table(CATEGORIES_TABLE_NAME)
    if FZIP_JOBS_TABLE:
        _fzip_jobs_table = dynamodb.Table(FZIP_JOBS_TABLE)

def get_transactions_table() -> Any:
    """Get the transactions table resource, initializing it if needed."""
    global _transactions_table
    if _transactions_table is None:
        initialize_tables()
    return _transactions_table

def get_accounts_table() -> Any:
    """Get the accounts table resource, initializing it if needed."""
    global _accounts_table
    if _accounts_table is None:
        initialize_tables()
    return _accounts_table

def get_files_table() -> Any:
    """Get the files table resource, initializing it if needed."""
    global _files_table
    if _files_table is None:
        initialize_tables()
    return _files_table

def get_file_maps_table() -> Any:
    """Get the file maps table resource, initializing it if needed."""
    global _file_maps_table
    if _file_maps_table is None:
        initialize_tables()
    return _file_maps_table

def get_analytics_data_table() -> Any:
    """Get the analytics data table resource, initializing it if needed."""
    global _analytics_data_table
    if _analytics_data_table is None:
        initialize_tables()
    return _analytics_data_table

def get_analytics_status_table() -> Any:
    """Get the analytics status table resource, initializing it if needed."""
    global _analytics_status_table
    if _analytics_status_table is None:
        initialize_tables()
    return _analytics_status_table

def get_categories_table() -> Any:
    """Get the categories table resource, initializing it if needed."""
    global _categories_table
    if _categories_table is None:
        initialize_tables()
    return _categories_table

def get_fzip_jobs_table() -> Any:
    """Get the FZIP jobs table resource, initializing it if needed."""
    global _fzip_jobs_table
    if _fzip_jobs_table is None:
        initialize_tables()
    return _fzip_jobs_table


class NotAuthorized(Exception):
    """Raised when a user is not authorized to access a resource."""
    pass

class NotFound(Exception):
    """Raised when a requested resource is not found."""
    pass

def check_user_owns_resource(resource_user_id: str, requesting_user_id: str) -> None:
    """Check if a user owns a resource."""
    if resource_user_id != requesting_user_id:
        raise NotAuthorized("Not authorized to access this resource")

def checked_mandatory_account(account_id: Optional[uuid.UUID], user_id: str) -> Account:
    """Check if account exists and user has access to it."""
    if not account_id:
        raise NotFound("Account ID is required")
    account = get_account(account_id)
    if not account:
        raise NotFound("Account not found")
    check_user_owns_resource(account.user_id, user_id)
    return account

def checked_optional_account(account_id: Optional[uuid.UUID], user_id: str) -> Optional[Account]:
    """Check if account exists and user has access to it, allowing None."""
    if not account_id:
        return None
    account = get_account(account_id)
    if not account:
        return None
    check_user_owns_resource(account.user_id, user_id)
    return account

def checked_mandatory_transaction_file(file_id: uuid.UUID, user_id: str) -> TransactionFile:
    """Check if file exists and user has access to it."""
    file = get_transaction_file(file_id)
    if not file:
        raise NotFound("File not found")
    check_user_owns_resource(file.user_id, user_id)
    return file

def checked_optional_transaction_file(file_id: Optional[uuid.UUID], user_id: str) -> Optional[TransactionFile]:
    """Check if file exists and user has access to it, allowing None."""
    if not file_id:
        return None
    file = get_transaction_file(file_id)
    if not file:
        return None
    check_user_owns_resource(file.user_id, user_id)
    return file

def checked_mandatory_file_map(file_map_id: Optional[uuid.UUID], user_id: str) -> FileMap:
    """Check if file map exists and user has access to it."""
    if not file_map_id:
        raise NotFound("FileMap ID is required")
    file_map = get_file_map(file_map_id)
    if not file_map:
        raise NotFound("File map not found")
    check_user_owns_resource(file_map.user_id, user_id)
    return file_map

def checked_optional_file_map(file_map_id: Optional[uuid.UUID], user_id: str) -> Optional[FileMap]:
    """Check if file map exists and user has access to it, allowing None."""
    if not file_map_id:
        return None
    file_map = get_file_map(file_map_id)
    if not file_map:
        return None
    check_user_owns_resource(file_map.user_id, user_id)
    return file_map

def get_account(account_id: uuid.UUID) -> Optional[Account]:
    """
    Retrieve an account by ID.
    
    Args:
        account_id: The unique identifier of the account
        
    Returns:
        Account object if found, None otherwise
    """
    try:
        response = get_accounts_table().get_item(Key={'accountId': str(account_id)})

        if 'Item' in response:
            return Account.from_dynamodb_item(response['Item'])
        return None
    except ClientError as e:
        logger.error(f"Error retrieving account {str(account_id)}: {str(e)}")
        raise


def list_user_accounts(user_id: str) -> List[Account]:
    """
    List all accounts for a specific user.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        List of Account objects
    """
    try:
        # Query using GSI for userId
        response = get_accounts_table().query(
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
    except ClientError as e:
        logger.error(f"Error listing accounts for user {user_id}: {str(e)}")
        raise


def create_account(account: Account):
    """
    Create a new account.
    
    Args:
        account: Account object
        
    """

    # Save to DynamoDB
    get_accounts_table().put_item(Item=account.to_dynamodb_item())




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
    get_accounts_table().put_item(Item=account.to_dynamodb_item())
    
    return account



def delete_account(account_id: uuid.UUID, user_id: str) -> bool: # Added user_id for authorization
    """
    Delete an account and handle any associated files.
    
    Args:
        account_id: The unique identifier of the account to delete
        user_id: The ID of the user making the request
        
    Returns:
        True if deleted successfully
    """
    try:
        # Check if the account exists and user has access
        account = checked_mandatory_account(account_id, user_id)
        
        # Get all files associated with this account
        associated_files = list_account_files(account_id) # This function doesn't currently check user_id for files
        logger.info(f"Found {len(associated_files)} files associated with account {str(account_id)}")
        
        # Delete each associated file and its transactions
        for file_item in associated_files:
            # Ensure user owns the file before deleting (important if list_account_files doesn't filter by user)
            # checked_mandatory_transaction_file(str(file_item.file_id), user_id) # This would re-fetch, maybe optimize
            if file_item.user_id != user_id:
                logger.warning(f"Skipping deletion of file {str(file_item.file_id)} as it's not owned by user {user_id}")
                continue
            try:
                # Delete the file and its transactions
                delete_transaction_file(file_item.file_id, user_id) # Pass user_id, file_item.file_id is UUID
                logger.info(f"Deleted file {str(file_item.file_id)} and its transactions")
            except Exception as file_error:
                logger.error(f"Error deleting file {str(file_item.file_id)}: {str(file_error)}")
                # Continue with other files
        
        # Delete the account
        get_accounts_table().delete_item(Key={'accountId': str(account_id)})
        logger.info(f"Account {str(account_id)} deleted successfully")
        
        return True
    except ClientError as e:
        logger.error(f"Error deleting account {str(account_id)}: {str(e)}")
        raise
    except NotAuthorized as e:
        logger.error(f"Authorization error deleting account {str(account_id)}: {str(e)}")
        raise


def get_transaction_file(file_id: uuid.UUID) -> Optional[TransactionFile]:
    """
    Retrieve a transaction file by ID.
    
    Args:
        file_id: The unique identifier of the file
        
    Returns:
        TransactionFile object if found, None otherwise
    """
    try:
        response = get_files_table().get_item(Key={'fileId': str(file_id)})
        
        if 'Item' in response:
            logger.info(f"3 {response['Item']}")
            tfd = TransactionFile.from_dynamodb_item(response['Item'])
            logger.info(f"2exact type {type(tfd.file_format)} {tfd.file_format}")
            return tfd
        return None
    except ClientError as e:
        logger.error(f"Error retrieving file {str(file_id)}: {str(e)}")
        raise


def list_account_files(account_id: uuid.UUID) -> List[TransactionFile]:
    """
    List all files for a specific account.
    
    Args:
        account_id: The account's unique identifier
        
    Returns:
        List of TransactionFile objects
    """
    try:
        # Query using GSI for accountId
        response = get_files_table().query(
            IndexName='AccountIdIndex',
            KeyConditionExpression=Key('accountId').eq(str(account_id))
        )
        logger.info(f"1 {response['Items']}")
        files = []
        for item in response.get('Items', []):
            files.append(TransactionFile.from_dynamodb_item(item))
            
        return files
    except ClientError as e:
        logger.error(f"Error listing files for account {str(account_id)}: {str(e)}")
        raise


def list_user_files(user_id: str) -> List[TransactionFile]:
    """
    List all files for a specific user.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        List of TransactionFile objects
    """
    try:
        # Query using GSI for userId
        response = get_files_table().query(
            IndexName='UserIdIndex',
            KeyConditionExpression=Key('userId').eq(user_id)
        )
        
        files = []
        for item in response.get('Items', []):
            try:
                files.append(TransactionFile.from_dynamodb_item(item))
            except Exception as e:
                logger.error(f"Error creating TransactionFile from item: {str(e)}")
                logger.error(f"Problematic item: {item}")
                raise
            
        return files
    except ClientError as e:
        logger.error(f"Error listing files for user {user_id}: {str(e)}")
        raise


def create_transaction_file(transaction_file: TransactionFile):
    """
    Create a new transaction file record.
    
    Args:
        transaction_file: TransactionFile object
        
    """
    try:
        # Save to DynamoDB
        get_files_table().put_item(Item=transaction_file.to_dynamodb_item())
        
    except ValueError as e:
        logger.error(f"Validation error creating file: {str(e)}")
        #log stack trace
        logger.error(traceback.format_exc())
        raise
    except ClientError as e:
        logger.error(f"Error creating file: {str(e)}")        
        logger.error(traceback.format_exc())
        raise


def update_transaction_file(file_id: uuid.UUID, user_id: str, updates: Dict[str, Any]):
    """
    Update a transaction file record in DynamoDB.
    
    Args:
        file_id: The unique identifier of the file
        updates: Dictionary of fields to update with their new values
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        transaction_file = checked_mandatory_transaction_file(file_id, user_id)
        
        # Create TransactionFileUpdate DTO
        update_dto = TransactionFileUpdate(**updates)
        
        # Use the model's method to update details
        transaction_file.update_with_data(update_dto)
        
        get_files_table().put_item(Item=transaction_file.to_dynamodb_item())
    except Exception as e:
        logger.error(f"Error updating transaction file {str(file_id)}: {str(e)}")

def update_transaction_file_object(transaction_file: TransactionFile):
    """
    Update a transaction file object in DynamoDB.
    """
    try:
        get_files_table().put_item(Item=transaction_file.to_dynamodb_item())
    except Exception as e:
        logger.error(f"Error updating transaction file object {str(transaction_file.file_id)}: {str(e)}")

def delete_transaction_file(file_id: uuid.UUID, user_id: str) -> bool: # Added user_id
    """
    Delete a transaction file and all its associated transactions.
    
    Args:
        file_id: The unique identifier of the file to delete
        user_id: The ID of the user requesting the deletion
        
    Returns:
        True if deleted successfully
    """
    try:
        # Check if the file exists and user owns it
        file_to_delete = checked_mandatory_transaction_file(file_id, user_id)
        
        # First delete all associated transactions
        # Note: delete_transactions_for_file does not currently perform user auth checks for each transaction
        transactions_deleted = delete_transactions_for_file(file_id)
        logger.info(f"Deleted {transactions_deleted} transactions for file {str(file_id)}")
        
        # Then delete the file metadata
        get_files_table().delete_item(Key={'fileId': str(file_id)})
        logger.info(f"Deleted file metadata for {str(file_id)}")
        
        return True
    except NotAuthorized as e:
        logger.error(f"Authorization error deleting file {str(file_id)}: {str(e)}")
        raise
    except ClientError as e:
        logger.error(f"Error deleting file {str(file_id)}: {str(e)}")
        raise
    except NotFound as e:
        logger.error(f"File not found error during deletion for file {str(file_id)}: {str(e)}")
        raise # Or return False, depending on desired behavior


def list_file_transactions(file_id: uuid.UUID) -> List[Transaction]:
    """
    List all transactions for a specific file.
    
    Args:
        file_id: The unique identifier of the file
        
    Returns:
        List of TransactionFile objects
    """
    try:
        response = get_transactions_table().query(
            IndexName='FileIdIndex',
            KeyConditionExpression=Key('fileId').eq(str(file_id))
        )
        return [Transaction.from_dynamodb_item(item) for item in response.get('Items', [])]
    except ClientError as e:
        logger.error(f"Error listing transactions for file {str(file_id)}: {str(e)}")
        raise


def _select_optimal_gsi(
    user_id: str,
    account_ids: Optional[List[uuid.UUID]] = None,
    category_ids: Optional[List[str]] = None,
    transaction_type: Optional[str] = None,
    ignore_dup: bool = False,
    uncategorized_only: bool = False,
    start_date_ts: Optional[int] = None,
    end_date_ts: Optional[int] = None
) -> Tuple[str, Any]:
    """
    Select the most optimal GSI based on filters to minimize data scanning.
    Returns (index_name, key_condition_expression).
    
    GSI Selection Priority:
    1. Single account filter -> AccountDateIndex 
    2. Single category filter -> CategoryDateIndex
    3. Status filter (ignore_dup/uncategorized) -> StatusDateIndex
    4. Transaction type filter -> TransactionTypeIndex
    5. Fallback -> UserIdIndex
    """
    
    # Helper function to add date range to key condition
    def _add_date_range(key_condition):
        if start_date_ts is not None and end_date_ts is not None:
            return key_condition & Key('date').between(start_date_ts, end_date_ts)
        elif start_date_ts is not None:
            return key_condition & Key('date').gte(start_date_ts)
        elif end_date_ts is not None:
            return key_condition & Key('date').lte(end_date_ts)
        return key_condition
    
    # 1. Single account filter (most selective for account-specific queries)
    if account_ids and len(account_ids) == 1:
        key_condition = Key('accountId').eq(str(account_ids[0]))
        key_condition = _add_date_range(key_condition)
        logger.debug(f"Using AccountDateIndex for account {account_ids[0]}")
        return 'AccountDateIndex', key_condition
    
    # 2. Single category filter (good for category analysis)  
    if category_ids and len(category_ids) == 1:
        key_condition = Key('primaryCategoryId').eq(category_ids[0])
        key_condition = _add_date_range(key_condition)
        logger.debug(f"Using CategoryDateIndex for category {category_ids[0]}")
        return 'CategoryDateIndex', key_condition
    
    # 3. Status filter (efficient for duplicate detection or status-specific queries)
    if ignore_dup:
        key_condition = Key('status').eq('processed')  # Assuming non-duplicates have 'processed' status
        key_condition = _add_date_range(key_condition)
        logger.debug("Using StatusDateIndex for ignore_dup filter")
        return 'StatusDateIndex', key_condition
    
    if uncategorized_only:
        # For uncategorized, we might use a specific status or fall back to UserIdIndex with filter
        # This depends on how uncategorized transactions are marked
        pass
    
    # 4. Transaction type filter
    if transaction_type and transaction_type.lower() != 'all':
        key_condition = Key('transactionType').eq(transaction_type)
        key_condition = _add_date_range(key_condition)
        logger.debug(f"Using TransactionTypeIndex for type {transaction_type}")
        return 'TransactionTypeIndex', key_condition
    
    # 5. Fallback to UserIdIndex (always works, but may be less efficient)
    key_condition = Key('userId').eq(user_id)
    key_condition = _add_date_range(key_condition)
    logger.debug("Using UserIdIndex (fallback)")
    return 'UserIdIndex', key_condition


def _get_remaining_filters(
    index_name: str,
    user_id: str,
    account_ids: Optional[List[uuid.UUID]] = None,
    category_ids: Optional[List[str]] = None,
    transaction_type: Optional[str] = None,
    ignore_dup: bool = False,
    uncategorized_only: bool = False,
    search_term: Optional[str] = None
) -> Dict[str, Any]:
    """
    Determine which filters still need to be applied via FilterExpression,
    excluding those already handled by the selected GSI.
    """
    filters = {}
    
    # Account filter - skip if using AccountDateIndex with single account
    if account_ids and not (index_name == 'AccountDateIndex' and len(account_ids) == 1):
        filters['account_ids'] = Attr('accountId').is_in([str(aid) for aid in account_ids])
    
    # Category filter - skip if using CategoryDateIndex with single category  
    if category_ids and not (index_name == 'CategoryDateIndex' and len(category_ids) == 1):
        filters['category_ids'] = Attr('primaryCategoryId').is_in(category_ids)
    
    # Transaction type filter - skip if using TransactionTypeIndex
    if (transaction_type and transaction_type.lower() != 'all' and 
        index_name != 'TransactionTypeIndex'):
        filters['transaction_type'] = Attr('transactionType').eq(transaction_type)
    
    # Status filter - skip if using StatusDateIndex for ignore_dup
    if ignore_dup and index_name != 'StatusDateIndex':
        filters['ignore_dup'] = Attr('status').ne('duplicate')
    
    # Uncategorized filter - always use FilterExpression (no dedicated GSI)
    if uncategorized_only:
        filters['uncategorized_only'] = Attr('primaryCategoryId').not_exists()
    
    # Search term - always use FilterExpression (no full-text GSI)
    if search_term:
        filters['search_term'] = Attr('description').contains(search_term)
    
    # User filter - add if not using UserIdIndex (for authorization)
    if index_name != 'UserIdIndex':
        filters['user_id'] = Attr('userId').eq(user_id)
    
    return filters


def list_user_transactions(
    user_id: str, 
    limit: int = 50, 
    last_evaluated_key: Optional[Dict[str, Any]] = None,
    start_date_ts: Optional[int] = None,
    end_date_ts: Optional[int] = None,
    account_ids: Optional[List[uuid.UUID]] = None, # Changed to List[uuid.UUID]
    category_ids: Optional[List[str]] = None,  # Added category_ids parameter
    transaction_type: Optional[str] = None,
    search_term: Optional[str] = None,
    sort_order_date: str = 'desc',
    ignore_dup: bool = False,
    uncategorized_only: bool = False
) -> Tuple[List[Transaction], Optional[Dict[str, Any]], int]:
    """
    List transactions for a user with filtering, date sorting, and pagination.
    Returns up to 'limit' transactions. May return fewer due to filtering - this is the 
    industry standard approach used by GitHub, Twitter, Stripe, etc.
    
    Args:
        user_id: The user ID to filter by
        limit: Maximum number of transactions to return (may return fewer due to filters)
        last_evaluated_key: For pagination
        start_date_ts: Start date filter (milliseconds since epoch)
        end_date_ts: End date filter (milliseconds since epoch)
        account_ids: List of account IDs to filter by
        category_ids: List of category IDs to filter by
        transaction_type: Transaction type to filter by
        search_term: Search term to filter descriptions
        sort_order_date: Sort order ('asc' or 'desc')
        ignore_dup: Whether to ignore duplicate transactions
        uncategorized_only: If True, only return transactions without categories
        
    Returns:
        Tuple of (transactions, last_evaluated_key, items_count)
    """
    try:
        table = get_transactions_table()
        if not table:
            logger.error("TRANSACTIONS_TABLE is not configured.")
            return [], None, 0

        # Smart GSI selection - choose the most selective index to minimize data scanning
        index_name, key_condition = _select_optimal_gsi(
            user_id=user_id,
            account_ids=account_ids,
            category_ids=category_ids,
            transaction_type=transaction_type,
            ignore_dup=ignore_dup,
            uncategorized_only=uncategorized_only,
            start_date_ts=start_date_ts,
            end_date_ts=end_date_ts
        )

        query_params: Dict[str, Any] = {
            'IndexName': index_name,
            'KeyConditionExpression': key_condition,
            'Limit': limit,  # Use requested limit directly - industry standard approach
            'ScanIndexForward': sort_order_date.lower() == 'asc'
        }

        if last_evaluated_key:
            query_params['ExclusiveStartKey'] = last_evaluated_key

        # Build filter expressions, excluding filters already handled by GSI selection
        filter_expressions = []
        
        # Only add filters that aren't already handled by the selected GSI
        remaining_filters = _get_remaining_filters(
            index_name=index_name,
            user_id=user_id,
            account_ids=account_ids,
            category_ids=category_ids,
            transaction_type=transaction_type,
            ignore_dup=ignore_dup,
            uncategorized_only=uncategorized_only,
            search_term=search_term
        )
        
        # Add non-None filters to the list
        filter_expressions.extend(filter_expr for filter_expr in remaining_filters.values() if filter_expr)
        
        # Combine all filters with AND logic
        if filter_expressions:
            from functools import reduce
            import operator
            query_params['FilterExpression'] = reduce(operator.and_, filter_expressions)

        logger.info(f"Using GSI: {index_name} for user {user_id}")
        logger.debug(f"DynamoDB query params: {query_params}")
        
        # Log optimization info
        if category_ids:
            logger.info(f"Filtering transactions by category IDs: {category_ids}")
        if filter_expressions:
            logger.info(f"Additional filters applied: {len(filter_expressions)} FilterExpressions")
        else:
            logger.info("No additional filters needed - all filtering done via GSI KeyCondition")
            
        response = table.query(**query_params)
        
        transactions = [Transaction.from_dynamodb_item(item) for item in response.get('Items', [])]
        new_last_evaluated_key = response.get('LastEvaluatedKey')
        
        # Count of items returned in this query response  
        items_in_current_response = len(transactions)
        
        logger.info(f"Query for user {user_id} returned {items_in_current_response} items (requested: {limit}). ScannedCount: {response.get('ScannedCount', 0)}, Count: {response.get('Count', 0)}")
        
        # Log filtering efficiency to help debug sparse data issues
        scanned_count = response.get('ScannedCount', 0)
        returned_count = response.get('Count', 0)
        if scanned_count > 0:
            filter_efficiency = (returned_count / scanned_count) * 100
            logger.info(f"Filter efficiency: {filter_efficiency:.1f}% ({returned_count}/{scanned_count} items passed filters)")

        return transactions, new_last_evaluated_key, items_in_current_response
            
    except ClientError as e:
        logger.error(f"Error querying transactions by user {user_id}: {str(e)}", exc_info=True)
        raise 
    except Exception as e:
        logger.error(f"Unexpected error in list_user_transactions for user {user_id}: {str(e)}", exc_info=True)
        raise


def create_transaction(transaction: Transaction):
    """
    Create a new transaction.
    
    Args:
        transaction: Transaction object
        
    """
    try:
        # Save to DynamoDB
        get_transactions_table().put_item(Item=transaction.to_dynamodb_item())
        
        return transaction
    except Exception as e:
        logger.error(f"Error creating transaction: {str(e)}")
        raise


def delete_transactions_for_file(file_id: uuid.UUID) -> int:
    """
    Delete all transactions associated with a file.
    
    Args:
        file_id: The ID of the file whose transactions should be deleted
        
    Returns:
        Number of transactions deleted
    """
    try:
        # Get all transactions for the file
        transactions = list_file_transactions(file_id)
        count = len(transactions)
        
        if count > 0:
            # Delete transactions in batches of 25 (DynamoDB limit)
            table = get_transactions_table()
            with table.batch_writer() as batch:
                for transaction_item in transactions: # Renamed to avoid conflict
                    batch.delete_item(Key={'transactionId': str(transaction_item.transaction_id)}) # transaction_item.transaction_id is UUID
            
            logger.info(f"Deleted {count} transactions for file {str(file_id)}")
        
        return count
    except ClientError as e:
        logger.error(f"Error deleting transactions for file {str(file_id)}: {str(e)}")
        raise


def delete_file_metadata(file_id: uuid.UUID) -> bool:
    """
    Delete a file metadata record from the files table.
    
    Args:
        file_id: The ID of the file to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        get_files_table().delete_item(Key={'fileId': str(file_id)})
        logger.info(f"Deleted file metadata for {str(file_id)}")
        return True
    except ClientError as e:
        logger.error(f"Error deleting file metadata {str(file_id)}: {str(e)}")
        raise


def get_file_map(file_map_id: Optional[uuid.UUID] = None) -> Optional[FileMap]:
    """
    Retrieve a file map by ID.
    
    Args:
        file_map_id: The unique identifier of the file map
        
    Returns:
        FileMap object if found, None otherwise
    """
    if not file_map_id:
        return None
    try:
        table = get_file_maps_table()
        if not table:
            logger.error("File maps table not initialized.")
            return None
        response = table.get_item(Key={'fileMapId': str(file_map_id)})

        if 'Item' in response:
            return FileMap.from_dynamodb_item(response['Item'])
        return None
    except ClientError as e:
        logger.error(f"Error retrieving file map {str(file_map_id)}: {str(e)}")
        raise


def get_account_default_file_map(account_id: uuid.UUID) -> Optional[FileMap]:
    """
    Get the default file map for an account.
    
    Args:
        account_id: ID of the account
        
    Returns:
        FileMap instance if found, None otherwise
    """
    try:
        # Get the account record
        account = get_account(account_id) 
        if not account:
            logger.warning(f"Account {str(account_id)} not found when trying to get default file map.")
            return None
            
        # Check for default field map
        default_file_map_id = account.default_file_map_id 
        if not default_file_map_id:
            return None
            
        # Get the field map
        return get_file_map(default_file_map_id) # default_file_map_id is already UUID from Account model
    except Exception as e:
        logger.error(f"Error getting default file map for account {str(account_id)}: {str(e)}")
        return None


def create_file_map(file_map: FileMap) -> None:
    """
    Create a new file map.
    
    Args:
        file_map: The FileMap object to create
    """
    try:
        get_file_maps_table().put_item(Item=file_map.to_dynamodb_item())
        logger.info(f"Successfully created file map {str(file_map.file_map_id)}")
    except ClientError as e:
        logger.error(f"Error creating file map {str(file_map.file_map_id)}: {str(e)}")
        raise


def update_file_map(file_map: FileMap) -> None:
    """
    Update an existing file map.
    
    Args:
        file_map: The FileMap object with updated details
    """
    try:
        get_file_maps_table().put_item(Item=file_map.to_dynamodb_item())
        logger.info(f"Successfully updated file map {str(file_map.file_map_id)}")
    except ClientError as e:
        logger.error(f"Error updating file map {str(file_map.file_map_id)}: {str(e)}")
        raise


def delete_file_map(file_map_id: uuid.UUID) -> bool:
    """
    Delete a file map by ID.
    
    Args:
        file_map_id: ID of the file map to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        get_file_maps_table().delete_item(
            Key={'fileMapId': str(file_map_id)}
        )
        return True
    except Exception as e:
        logger.error(f"Error deleting file map: {str(e)}")
        return False


def list_file_maps_by_user(user_id: str) -> List[FileMap]:
    """
    List all file maps for a specific user.
    
    Args:
        user_id: ID of the user
        
    Returns:
        List of FileMap instances
    """
    try:
        response = get_file_maps_table().query(
            IndexName='UserIdIndex',
            KeyConditionExpression=Key('userId').eq(user_id)
        )
        return [FileMap.from_dynamodb_item(item) for item in response.get('Items', [])]
    except ClientError as e:
        logger.error(f"Error listing file maps for user {user_id}: {str(e)}")
        raise


def list_account_file_maps(account_id: str) -> List[FileMap]:
    """
    List all file maps for a specific account.
    
    Args:
        account_id: The account's unique identifier
        
    Returns:
        List of FileMap objects
    """
    try:
        # Query using GSI for accountId
        response = get_file_maps_table().query(
            IndexName='AccountIdIndex',
            KeyConditionExpression=Key('accountId').eq(str(account_id))
        )
        return [FileMap.from_dynamodb_item(item) for item in response.get('Items', [])]
    except Exception as e:
        logger.error(f"Error listing file maps for account {str(account_id)}: {str(e)}")
        raise


def list_account_transactions(account_id: str, limit: int = 50, last_evaluated_key: Optional[Dict] = None) -> List[Transaction]:
    """
    List transactions for a specific account with pagination.
    
    Note: This function requires a GSI named 'AccountDateIndex' with:
        - Partition key: accountId
        - Sort key: date
        - Additional attributes: importOrder
    
    Args:
        account_id: The account ID to list transactions for
        limit: Maximum number of transactions to return
        last_evaluated_key: Key to start from for pagination
        
    Returns:
        List of Transaction objects sorted by date (ascending)
    """
    try:
        # Query transactions table using AccountDateIndex
        # This will return transactions sorted by date
        query_params = {
            'IndexName': 'AccountDateIndex',
            'KeyConditionExpression': Key('accountId').eq(str(account_id)),
            'FilterExpression': Attr('status').ne('duplicate'),
            'Limit': limit,
            'ScanIndexForward': True  # Sort in ascending order (oldest first)
        }
        
        if last_evaluated_key:
            query_params['ExclusiveStartKey'] = last_evaluated_key
            
        response = get_transactions_table().query(**query_params)
        
        # Convert items to Transaction objects
        transactions = [Transaction.from_dynamodb_item(item) for item in response.get('Items', [])]
        
        # Sort by import order within each date
        transactions.sort(key=lambda x: (x.date, x.import_order or 0))
            
        return transactions
        
    except Exception as e:
        logger.error(f"Error listing transactions for account {str(account_id)}: {str(e)}")
        raise


def update_transaction_statuses_by_status(old_status: str, new_status: str) -> int:
    """
    Update all transactions with a specific status to a new status.
    Uses a GSI on the status field for efficient querying.
    
    Args:
        old_status: The current status to match
        new_status: The new status to set
        
    Returns:
        Number of transactions updated
    """
    try:
        table = get_transactions_table()
        count = 0
        
        # Query using StatusIndex GSI
        response = table.query(
            IndexName='StatusIndex',
            KeyConditionExpression=Key('status').eq(old_status)
        )
        
        # Process in batches of 25 (DynamoDB limit)
        while True:
            items = response.get('Items', [])
            if not items:
                break
                
            # Update items in batches
            with table.batch_writer() as batch:
                for item in items:
                    batch.put_item(
                        Item={
                            **item,
                            'status': new_status,
                            'updatedAt': int(datetime.now(timezone.utc).timestamp() * 1000) # Also update updatedAt
                        }
                    )
                    count += 1
            
            # Check if there are more items
            if 'LastEvaluatedKey' not in response:
                break
                
            response = table.query(
                IndexName='StatusIndex',
                KeyConditionExpression=Key('status').eq(old_status),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
        
        logger.info(f"Updated {count} transactions from status '{old_status}' to '{new_status}'")
        return count
        
    except Exception as e:
        logger.error(f"Error updating transaction statuses: {str(e)}")
        raise


def update_file_account_id(file_id: str, account_id: str) -> None:
    """
    Update the accountId of a file in the files table.
    Args:
        file_id: The unique identifier of the file
        account_id: The account ID to associate with the file
    """
    try:
        table = get_files_table()
        update_expression = "SET accountId = :accountId, updatedAt = :updatedAt"
        expression_attribute_values = {":accountId": str(account_id), ":updatedAt": int(datetime.now(timezone.utc).timestamp() * 1000)}
        table.update_item(
            Key={'fileId': str(file_id)},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
    except Exception as e:
        logger.error(f"Error updating accountId for file {str(file_id)}: {str(e)}")
        raise


def update_file_field_map(file_id: str, field_map_id: str) -> None:
    """
    Update the fieldMapId of a file in the files table.
    Args:
        file_id: The unique identifier of the file
        field_map_id: The field map ID to associate with the file
    """
    try:
        table = get_files_table()
        update_expression = "SET fieldMapId = :fieldMapId, updatedAt = :updatedAt"
        expression_attribute_values = {":fieldMapId": str(field_map_id), ":updatedAt": int(datetime.now(timezone.utc).timestamp() * 1000)}
        table.update_item(
            Key={'fileId': str(file_id)},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
    except Exception as e:
        logger.error(f"Error updating fieldMapId for file {str(file_id)}: {str(e)}")
        raise


def get_transaction_by_account_and_hash(account_id: Union[str, uuid.UUID], transaction_hash: int) -> Optional[Transaction]:
    """
    Retrieve a specific transaction by account ID and transaction hash.
    Args:
        account_id: The account ID
        transaction_hash: The transaction hash
    Returns:
        Transaction object if found, None otherwise
    """
    try:
        response = get_transactions_table().query(
            IndexName='TransactionHashIndex', 
            KeyConditionExpression=Key('accountId').eq(str(account_id)) & Key('transactionHash').eq(transaction_hash)
        )
        if response.get('Items'):
            return Transaction.from_dynamodb_item(response['Items'][0])
        return None
    except ClientError as e:
        logger.error(f"Error retrieving transaction by account {str(account_id)} and hash {transaction_hash}: {e}")
        raise


def check_duplicate_transaction(transaction: Transaction) -> bool: 
    """
    Check if a transaction already exists for the given account using numeric hash.
    
    Args:
        transaction: Transaction object
        
    Returns:
        bool: True if duplicate found, False otherwise
    """
    try:
        logger.info(f"Entering check_duplicate_transaction for transaction: {transaction}")
        if transaction.transaction_hash is None or transaction.account_id is None:
            logger.error(f"Transaction hash or account ID is None for transaction: {transaction}")
            raise ValueError("Transaction hash or account ID is None")
        existing = get_transaction_by_account_and_hash(transaction.account_id, transaction.transaction_hash)
        if existing:
            logger.info(f"Found existing transaction: hash={existing.transaction_hash} date={existing.date} amount={existing.amount} description={existing.description}")
        else:
            logger.info(f"No existing transaction found for hash={transaction.transaction_hash}")
        return existing is not None
    except Exception as e:
        logger.error(f"Error checking for duplicate transaction: {str(e)}")
        return False 


def update_transaction(transaction: Transaction) -> None:
    """
    Update an existing transaction in DynamoDB.
    
    Args:
        transaction: Transaction object to update
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        get_transactions_table().put_item(Item=transaction.to_dynamodb_item())
    except ClientError as e:
        logger.error(f"Error updating transaction {str(transaction.transaction_id)}: {str(e)}")
        raise e

def get_last_transaction_date(account_id: Union[str, uuid.UUID]) -> Optional[int]:
    """
    Get the most recent transaction date for a specific account.
    Only considers transactions with status starting with 'new' (non-duplicates).
    
    Args:
        account_id: The account ID
        
    Returns:
        Transaction date as milliseconds since epoch, or None if no transactions found
    """
    try:
        # Query the most recent non-duplicate transaction for this account
        # The statusDate field is a composite key of format "status#timestamp"
        response = get_transactions_table().query(
            IndexName='AccountStatusDateIndex',
            KeyConditionExpression=Key('accountId').eq(str(account_id)) & Key('statusDate').begins_with('new#'),
            Limit=1,
            ScanIndexForward=False  # Sort in descending order to get most recent first
        )
        
        if response.get('Items'):
            return response['Items'][0].get('date')
        return None
        
    except Exception as e:
        logger.error(f"Error getting last transaction date for account {str(account_id)}: {str(e)}")
        return None

def get_latest_transaction(account_id: Union[str, uuid.UUID]) -> Optional[Transaction]:
    """
    Get the most recent transaction for a specific account.
    Only considers transactions with status starting with 'new' (non-duplicates).
    
    Args:
        account_id: The account ID
        
    Returns:
        Transaction object or None if no transactions found
    """
    try:
        # Query the most recent non-duplicate transaction for this account
        # The statusDate field is a composite key of format "status#timestamp"
        response = get_transactions_table().query(
            IndexName='AccountStatusDateIndex',
            KeyConditionExpression=Key('accountId').eq(str(account_id)) & Key('statusDate').begins_with('new#'),
            Limit=1,
            ScanIndexForward=False  # Sort in descending order to get most recent first
        )
        logger.info(f"DB: get_latest_transaction response: {response}")
        
        if response.get('Items'):
            return Transaction.from_dynamodb_item(response['Items'][0])
        return None
        
    except Exception as e:
        logger.error(f"Error getting latest transaction for account {str(account_id)}: {str(e)}")
        return None


def create_category_in_db(category: Category) -> Category:
    """Persist a new category to DynamoDB."""
    table = get_categories_table()
    if not table:
        logger.error("DB: Categories table not initialized for create_category_in_db")
        raise ConnectionError("Database table not initialized")
    
    try:
        # Category is already a Pydantic model, so use model_dump()
        table.put_item(Item=category.to_dynamodb_item())
        logger.info(f"DB: Category {str(category.categoryId)} created successfully for user {category.userId}.")
        return category
    except ClientError as e:
        logger.error(f"DB: Error creating category {str(category.categoryId)}: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"DB: Unexpected error creating category {str(category.categoryId)}: {str(e)}", exc_info=True)
        raise

def get_category_by_id_from_db(category_id: uuid.UUID, user_id: str) -> Optional[Category]:
    table = get_categories_table()
    if not table:
        logger.error("DB: Categories table not initialized for get_category_by_id_from_db")
        return None
    logger.debug(f"DB: Getting category {str(category_id)} for user {user_id}")
    response = table.get_item(Key={'categoryId': str(category_id)})
    item = response.get('Item')
    if item and item.get('userId') == user_id:
        return Category.from_dynamodb_item(item)
    elif item:
        logger.warning(f"User {user_id} attempted to access category {str(category_id)} owned by {item.get('userId')}")
        return None
    return None

def list_categories_by_user_from_db(user_id: str, parent_category_id: Optional[uuid.UUID] = None, top_level_only: bool = False) -> List[Category]:
    table = get_categories_table()
    if not table:
        logger.error("DB: Categories table not initialized for list_categories_by_user_from_db")
        return []
    logger.debug(f"DB: Listing categories for user {user_id}, parent: {str(parent_category_id) if parent_category_id else None}, top_level: {top_level_only}")
    params: Dict[str, Any] = {}
    filter_expressions = []
    if parent_category_id is not None:
        # Removed check for parent_category_id.lower() == "null" as it's now UUID
        params['IndexName'] = 'UserIdParentCategoryIdIndex' # Assumes this index exists with parentCategoryId as string
        params['KeyConditionExpression'] = Key('userId').eq(user_id) & Key('parentCategoryId').eq(str(parent_category_id))
    else: 
        params['IndexName'] = 'UserIdIndex'
        params['KeyConditionExpression'] = Key('userId').eq(user_id)
        if top_level_only:
            filter_expressions.append(Attr('parentCategoryId').not_exists())
    
    if filter_expressions:
        final_filter_expression = filter_expressions[0]
        for i in range(1, len(filter_expressions)):
            final_filter_expression = final_filter_expression & filter_expressions[i]
        params['FilterExpression'] = final_filter_expression

    all_items_raw = []
    current_params = params.copy() # To avoid modifying params for subsequent calls if pagination is added here
    while True:
        response = table.query(**current_params)
        all_items_raw.extend(response.get('Items', []))
        if 'LastEvaluatedKey' not in response:
            break
        current_params['ExclusiveStartKey'] = response['LastEvaluatedKey']
    return [Category.from_dynamodb_item(item) for item in all_items_raw]

def update_category_in_db(category_id: uuid.UUID, user_id: str, update_data: Dict[str, Any]) -> Optional[Category]:
    """
    Update an existing category in DynamoDB.
    
    Args:
        category_id: The unique identifier of the category to update
        user_id: The ID of the user making the request
        update_data: Dictionary containing fields to update
        
    Returns:
        Updated Category object if successful, None if category not found
    """
    # Retrieve the existing category
    category = get_category_by_id_from_db(category_id, user_id)
    if not category:
        logger.warning(f"DB: Category {str(category_id)} not found or user {user_id} has no access.")
        return None

    if not update_data:
        logger.info(f"DB: No update data provided for category {str(category_id)}. Returning existing.")
        return category

    try:
        # Diagnostic logging
        logger.info(f"DIAG: update_category_in_db called with update_data keys: {list(update_data.keys())}")
        if 'rules' in update_data:
            rules = update_data['rules']
            logger.info(f"DIAG: update_data contains {len(rules)} rules")
            for i, rule in enumerate(rules):
                logger.info(f"DIAG: update_data rule {i}: type={type(rule)}, is_CategoryRule={isinstance(rule, CategoryRule)}")
        
        # Create a CategoryUpdate DTO from the update_data
        logger.info("DIAG: Creating CategoryUpdate DTO...")
        category_update_dto = CategoryUpdate(**update_data)
        logger.info("DIAG: CategoryUpdate DTO created successfully")
        
        # Check the DTO's rules
        if hasattr(category_update_dto, 'rules') and category_update_dto.rules:
            logger.info(f"DIAG: CategoryUpdate DTO has {len(category_update_dto.rules)} rules")
            for i, rule in enumerate(category_update_dto.rules):
                logger.info(f"DIAG: DTO rule {i}: type={type(rule)}, is_CategoryRule={isinstance(rule, CategoryRule)}")
        
        # Use the model's method to update details
        logger.info("DIAG: Calling update_category_details...")
        category.update_category_details(category_update_dto)
        logger.info("DIAG: update_category_details completed")
        
        # Check category rules after update
        logger.info(f"DIAG: After update, category has {len(category.rules)} rules")
        for i, rule in enumerate(category.rules):
            logger.info(f"DIAG: Post-update rule {i}: type={type(rule)}, is_CategoryRule={isinstance(rule, CategoryRule)}")
        
        # Save updates to DynamoDB
        logger.info("DIAG: Calling to_dynamodb_item...")
        get_categories_table().put_item(Item=category.to_dynamodb_item())
        
        logger.info(f"DB: Category {str(category_id)} updated successfully.")
        return category
        
    except ValidationError as e:
        logger.error(f"DB: Validation error updating category {str(category_id)}: {str(e)}")
        raise ValueError(f"Invalid update data: {str(e)}")
    except ClientError as e:
        logger.error(f"DB: Error updating category {str(category_id)}: {str(e)}", exc_info=True)
        raise 
    except Exception as e:
        logger.error(f"DB: Unexpected error updating category {str(category_id)}: {str(e)}", exc_info=True)
        raise

def delete_category_from_db(category_id: uuid.UUID, user_id: str) -> bool:
    table = get_categories_table()
    if not table:
        logger.error("DB: Categories table not initialized for delete_category_from_db")
        return False
    logger.debug(f"DB: Deleting category {str(category_id)} for user {user_id}")
    category_to_delete = get_category_by_id_from_db(category_id, user_id) # Use the util version
    if not category_to_delete:
        return False
    child_categories = list_categories_by_user_from_db(user_id, parent_category_id=category_id) # Use the util version
    if child_categories:
        logger.warning(f"Attempt to delete category {str(category_id)} which has child categories.")
        raise ValueError("Cannot delete category: it has child categories.")
    
    # Clean up transaction references before deleting the category
    logger.info(f"DB: Cleaning up transaction references for category {str(category_id)}")
    transactions_cleaned = _cleanup_transaction_category_references(category_id, user_id)
    logger.info(f"DB: Cleaned up {transactions_cleaned} transactions that referenced category {str(category_id)}")
    
    table.delete_item(Key={'categoryId': str(category_id)})
    return True


def _cleanup_transaction_category_references(category_id: uuid.UUID, user_id: str) -> int:
    """
    Clean up all transaction references to a category before deleting it.
    
    Args:
        category_id: The category ID to remove from transactions
        user_id: The user ID to limit scope of cleanup
        
    Returns:
        Number of transactions that were cleaned up
    """
    try:
        cleaned_count = 0
        
        # Get all transactions that reference this category either as primary or in categories list
        # We need to scan through all user transactions since DynamoDB doesn't have a direct way
        # to query by category references efficiently
        
        # Get transactions in batches to avoid memory issues
        last_evaluated_key = None
        batch_size = 1000
        
        while True:
            # Get batch of transactions
            transactions, last_evaluated_key, _ = list_user_transactions(
                user_id=user_id,
                limit=batch_size,
                last_evaluated_key=last_evaluated_key,
                uncategorized_only=False  # Get all transactions, not just uncategorized ones
            )
            
            if not transactions:
                break
            
            # Process transactions in this batch
            for transaction in transactions:
                transaction_updated = False
                
                # Check if this transaction references the category being deleted
                if transaction.primary_category_id == category_id:
                    # Remove primary category reference
                    transaction.primary_category_id = None
                    transaction_updated = True
                    logger.debug(f"DB: Removed primary category reference from transaction {transaction.transaction_id}")
                
                # Check categories list for references to this category
                if transaction.categories:
                    original_categories_count = len(transaction.categories)
                    # Remove any category assignments that reference the deleted category
                    transaction.categories = [
                        cat for cat in transaction.categories 
                        if cat.category_id != category_id
                    ]
                    
                    if len(transaction.categories) < original_categories_count:
                        transaction_updated = True
                        logger.debug(f"DB: Removed category assignment from transaction {transaction.transaction_id}")
                        
                        # If we removed categories and there's no primary category, 
                        # set a new primary from remaining confirmed categories
                        if not transaction.primary_category_id and transaction.confirmed_categories:
                            transaction.primary_category_id = transaction.confirmed_categories[0].category_id
                            logger.debug(f"DB: Set new primary category for transaction {transaction.transaction_id}")
                
                # Update transaction if it was modified
                if transaction_updated:
                    update_transaction(transaction)
                    cleaned_count += 1
            
            # If we got fewer transactions than requested, we're done
            if not last_evaluated_key:
                break
        
        return cleaned_count
        
    except Exception as e:
        logger.error(f"DB: Error cleaning up transaction references for category {str(category_id)}: {str(e)}", exc_info=True)
        raise

# =============================================================================
# Analytics Data Functions
# =============================================================================

def store_analytics_data(analytics_data: AnalyticsData) -> None:
    """
    Store computed analytics data in DynamoDB.
    
    Args:
        analytics_data: The AnalyticsData object to store
        
    Raises:
        ClientError: If there's a DynamoDB error
    """
    try:
        item = analytics_data.to_dynamodb_item()
        get_analytics_data_table().put_item(Item=item)
        logger.info(f"Stored analytics data: {analytics_data.analytic_type.value} for user {analytics_data.user_id}, period {analytics_data.time_period}")
    except ClientError as e:
        logger.error(f"Error storing analytics data: {str(e)}")
        raise

def get_analytics_data(user_id: str, analytic_type: AnalyticType, time_period: str, account_id: Optional[str] = None) -> Optional[AnalyticsData]:
    """
    Retrieve specific analytics data from DynamoDB.
    
    Args:
        user_id: The user ID
        analytic_type: The type of analytics
        time_period: The time period (e.g., '2024-12')
        account_id: Optional account ID (None for cross-account)
        
    Returns:
        AnalyticsData object if found, None otherwise
    """
    try:
        pk = f"{user_id}#{analytic_type.value}"
        account_part = account_id or 'ALL'
        sk = f"{time_period}#{account_part}"
        
        response = get_analytics_data_table().get_item(
            Key={'pk': pk, 'sk': sk}
        )
        
        if 'Item' in response:
            return AnalyticsData.from_dynamodb_item(response['Item'])
        return None
    except ClientError as e:
        logger.error(f"Error retrieving analytics data: {str(e)}")
        raise

def list_analytics_data_for_user(user_id: str, analytic_type: AnalyticType, time_range_prefix: Optional[str] = None) -> List[AnalyticsData]:
    """
    List analytics data for a user and analytic type, optionally filtered by time range.
    
    Args:
        user_id: The user ID
        analytic_type: The type of analytics
        time_range_prefix: Optional time range prefix (e.g., '2024' for all of 2024)
        
    Returns:
        List of AnalyticsData objects
    """
    try:
        pk = f"{user_id}#{analytic_type.value}"
        
        if time_range_prefix:
            # Query with time range filter
            response = get_analytics_data_table().query(
                KeyConditionExpression=Key('pk').eq(pk) & Key('sk').begins_with(time_range_prefix)
            )
        else:
            # Query all for this analytic type
            response = get_analytics_data_table().query(
                KeyConditionExpression=Key('pk').eq(pk)
            )
        
        analytics_data = []
        for item in response.get('Items', []):
            analytics_data.append(AnalyticsData.from_dynamodb_item(item))
        
        return analytics_data
    except ClientError as e:
        logger.error(f"Error listing analytics data: {str(e)}")
        raise

def batch_store_analytics_data(analytics_list: List[AnalyticsData]) -> None:
    """
    Store multiple analytics data objects in batch.
    
    Args:
        analytics_list: List of AnalyticsData objects to store
        
    Raises:
        ClientError: If there's a DynamoDB error
    """
    try:
        # Process in batches of 25 (DynamoDB limit)
        for i in range(0, len(analytics_list), 25):
            batch = analytics_list[i:i+25]
            
            with get_analytics_data_table().batch_writer() as batch_writer:
                for analytics_data in batch:
                    item = analytics_data.to_dynamodb_item()
                    batch_writer.put_item(Item=item)
        
        logger.info(f"Batch stored {len(analytics_list)} analytics data objects")
    except ClientError as e:
        logger.error(f"Error batch storing analytics data: {str(e)}")
        raise

def delete_analytics_data(user_id: str, analytic_type: AnalyticType, time_period: str, account_id: Optional[str] = None) -> bool:
    """
    Delete specific analytics data from DynamoDB.
    
    Args:
        user_id: The user ID
        analytic_type: The type of analytics
        time_period: The time period
        account_id: Optional account ID
        
    Returns:
        True if deleted, False if not found
    """
    try:
        pk = f"{user_id}#{analytic_type.value}"
        account_part = account_id or 'ALL'
        sk = f"{time_period}#{account_part}"
        
        response = get_analytics_data_table().delete_item(
            Key={'pk': pk, 'sk': sk},
            ReturnValues='ALL_OLD'
        )
        
        return 'Attributes' in response
    except ClientError as e:
        logger.error(f"Error deleting analytics data: {str(e)}")
        raise

# =============================================================================
# Analytics Processing Status Functions
# =============================================================================

def store_analytics_status(status: AnalyticsProcessingStatus) -> None:
    """
    Store analytics processing status in DynamoDB.
    
    Args:
        status: The AnalyticsProcessingStatus object to store
        
    Raises:
        ClientError: If there's a DynamoDB error
    """
    try:
        item = status.to_dynamodb_item()
        get_analytics_status_table().put_item(Item=item)
        logger.info(f"Stored analytics status: {status.analytic_type.value} for user {status.user_id}")
    except ClientError as e:
        logger.error(f"Error storing analytics status: {str(e)}")
        raise

def get_analytics_status(user_id: str, analytic_type: AnalyticType, account_id: Optional[str] = None) -> Optional[AnalyticsProcessingStatus]:
    """
    Retrieve analytics processing status from DynamoDB.
    
    Args:
        user_id: The user ID
        analytic_type: The type of analytics
        account_id: Optional account ID
        
    Returns:
        AnalyticsProcessingStatus object if found, None otherwise
    """
    try:
        account_part = account_id or 'ALL'
        sk = f"{analytic_type.value}#{account_part}"
        
        response = get_analytics_status_table().get_item(
            Key={'pk': user_id, 'sk': sk}
        )
        
        if 'Item' in response:
            return AnalyticsProcessingStatus.from_dynamodb_item(response['Item'])
        return None
    except ClientError as e:
        logger.error(f"Error retrieving analytics status: {str(e)}")
        raise

def list_analytics_status_for_user(user_id: str) -> List[AnalyticsProcessingStatus]:
    """
    List all analytics processing status for a user.
    
    Args:
        user_id: The user ID
        
    Returns:
        List of AnalyticsProcessingStatus objects
    """
    try:
        response = get_analytics_status_table().query(
            KeyConditionExpression=Key('pk').eq(user_id)
        )
        
        status_list = []
        for item in response.get('Items', []):
            status_list.append(AnalyticsProcessingStatus.from_dynamodb_item(item))
        
        return status_list
    except ClientError as e:
        logger.error(f"Error listing analytics status: {str(e)}")
        raise

def update_analytics_status(user_id: str, analytic_type: AnalyticType, updates: Dict[str, Any], account_id: Optional[str] = None) -> Optional[AnalyticsProcessingStatus]:
    """
    Update analytics processing status.
    
    Args:
        user_id: The user ID
        analytic_type: The type of analytics
        updates: Dictionary of updates to apply
        account_id: Optional account ID
        
    Returns:
        Updated AnalyticsProcessingStatus object if successful, None otherwise
    """
    try:
        from datetime import date, datetime
        
        account_part = account_id or 'ALL'
        sk = f"{analytic_type.value}#{account_part}"
        
        # Build update expression
        update_expression = "SET "
        expression_values = {}
        expression_names = {}
        
        for key, value in updates.items():
            if key in ['lastUpdated', 'lastComputedDate', 'dataAvailableThrough']:
                # Handle date/datetime fields
                if isinstance(value, (date, datetime)):
                    expression_values[f':{key}'] = value.isoformat()
                else:
                    expression_values[f':{key}'] = value
            elif key == 'status' and hasattr(value, 'value'):
                # Handle enum fields
                expression_values[f':{key}'] = value.value
            elif key == 'computationNeeded':
                # Handle Binary type for computationNeeded
                from boto3.dynamodb.types import Binary
                expression_values[f':{key}'] = Binary(b'\x01' if value else b'\x00')
            else:
                expression_values[f':{key}'] = value
            
            expression_names[f'#{key}'] = key
            update_expression += f"#{key} = :{key}, "
        
        # Remove trailing comma and space
        update_expression = update_expression.rstrip(', ')
        
        response = get_analytics_status_table().update_item(
            Key={'pk': user_id, 'sk': sk},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames=expression_names,
            ReturnValues='ALL_NEW'
        )
        
        if 'Attributes' in response:
            return AnalyticsProcessingStatus.from_dynamodb_item(response['Attributes'])
        return None
    except ClientError as e:
        logger.error(f"Error updating analytics status: {str(e)}")
        raise

def list_stale_analytics(computation_needed_only: bool = True) -> List[AnalyticsProcessingStatus]:
    """
    List analytics that need recomputation (stale analytics).
    
    Args:
        computation_needed_only: If True, only return items where computation_needed=True
        
    Returns:
        List of AnalyticsProcessingStatus objects that need recomputation
    """
    try:
        if computation_needed_only:
            # Use the GSI to efficiently query for records that need computation
            # Use Binary type for the query
            from boto3.dynamodb.types import Binary
            binary_true = Binary(b'\x01')  # Binary type for true
            
            response = get_analytics_status_table().query(
                IndexName='ComputationNeededIndex',
                KeyConditionExpression=Key('computationNeeded').eq(binary_true),
                # Order by lastUpdated to process oldest first
                ScanIndexForward=True
            )
        else:
            # If we need all records, fall back to scan
            response = get_analytics_status_table().scan()
        
        status_list = []
        for item in response.get('Items', []):
            status_list.append(AnalyticsProcessingStatus.from_dynamodb_item(item))
        
        return status_list
    except ClientError as e:
        logger.error(f"Error listing stale analytics: {str(e)}")
        raise 


# =============================================================================
# FZIP Jobs Functions (Unified Import/Export)
# =============================================================================

def create_fzip_job(fzip_job: FZIPJob) -> None:
    """
    Create a new FZIP job in DynamoDB.
    
    Args:
        fzip_job: The FZIPJob object to store
        
    Raises:
        ClientError: If there's a DynamoDB error
    """
    try:
        item = fzip_job.to_dynamodb_item()
        get_fzip_jobs_table().put_item(Item=item)
        logger.info(f"Created FZIP job: {fzip_job.job_id} for user {fzip_job.user_id}")
    except ClientError as e:
        logger.error(f"Error creating FZIP job: {str(e)}")
        raise


def get_fzip_job(job_id: str, user_id: str) -> Optional[FZIPJob]:
    """
    Retrieve a FZIP job by ID and user ID.
    
    Args:
        job_id: The FZIP job ID
        user_id: The user ID (for access control)
        
    Returns:
        FZIPJob object if found and owned by user, None otherwise
    """
    try:
        response = get_fzip_jobs_table().get_item(Key={'jobId': job_id})
        
        if 'Item' in response:
            item = response['Item']
            # Check user ownership
            if item.get('userId') == user_id:
                return FZIPJob.from_dynamodb_item(item)
            else:
                logger.warning(f"User {user_id} attempted to access FZIP job {job_id} owned by {item.get('userId')}")
                return None
        return None
    except ClientError as e:
        logger.error(f"Error retrieving FZIP job {job_id}: {str(e)}")
        return None


def update_fzip_job(fzip_job: FZIPJob) -> None:
    """
    Update an existing FZIP job in DynamoDB.
    
    Args:
        fzip_job: The FZIPJob object with updated details
        
    Raises:
        ClientError: If there's a DynamoDB error
    """
    try:
        item = fzip_job.to_dynamodb_item()
        get_fzip_jobs_table().put_item(Item=item)
        logger.info(f"Updated FZIP job: {fzip_job.job_id}")
    except ClientError as e:
        logger.error(f"Error updating FZIP job {fzip_job.job_id}: {str(e)}")
        raise


def list_user_fzip_jobs(user_id: str, job_type: Optional[str] = None, limit: int = 20, last_evaluated_key: Optional[Dict[str, Any]] = None) -> Tuple[List[FZIPJob], Optional[Dict[str, Any]]]:
    """
    List FZIP jobs for a user with pagination and optional job type filtering.
    
    Args:
        user_id: The user ID
        job_type: Optional job type filter ('export' or 'import')
        limit: Maximum number of jobs to return
        last_evaluated_key: For pagination
        
    Returns:
        Tuple of (fzip_jobs_list, next_pagination_key)
    """
    try:
        if job_type:
            # Use UserJobTypeIndex for filtering by job type
            query_params = {
                'IndexName': 'UserJobTypeIndex',
                'KeyConditionExpression': Key('userId').eq(user_id) & Key('jobType').eq(job_type),
                'Limit': limit,
                'ScanIndexForward': False  # Most recent first
            }
        else:
            # Use UserIdIndex for all jobs
            query_params = {
                'IndexName': 'UserIdIndex',
                'KeyConditionExpression': Key('userId').eq(user_id),
                'Limit': limit,
                'ScanIndexForward': False  # Most recent first
            }
        
        if last_evaluated_key:
            query_params['ExclusiveStartKey'] = last_evaluated_key
        
        response = get_fzip_jobs_table().query(**query_params)
        
        fzip_jobs = []
        for item in response.get('Items', []):
            try:
                fzip_job = FZIPJob.from_dynamodb_item(item)
                fzip_jobs.append(fzip_job)
            except Exception as e:
                logger.error(f"Error creating FZIPJob from item: {str(e)}")
                continue
        
        pagination_key = response.get('LastEvaluatedKey')
        
        logger.info(f"Listed {len(fzip_jobs)} FZIP jobs for user {user_id}")
        return fzip_jobs, pagination_key
        
    except ClientError as e:
        logger.error(f"Error listing FZIP jobs for user {user_id}: {str(e)}")
        return [], None


def delete_fzip_job(job_id: str, user_id: str) -> bool:
    """
    Delete a FZIP job.
    
    Args:
        job_id: The FZIP job ID
        user_id: The user ID (for access control)
        
    Returns:
        True if deleted, False if not found or access denied
    """
    try:
        # First verify ownership
        fzip_job = get_fzip_job(job_id, user_id)
        if not fzip_job:
            logger.warning(f"FZIP job {job_id} not found or access denied for user {user_id}")
            return False
        
        # Delete the job
        get_fzip_jobs_table().delete_item(Key={'jobId': job_id})
        logger.info(f"Deleted FZIP job: {job_id} for user {user_id}")
        return True
        
    except ClientError as e:
        logger.error(f"Error deleting FZIP job {job_id}: {str(e)}")
        return False


def cleanup_expired_fzip_jobs() -> int:
    """
    Clean up expired FZIP jobs.
    
    Returns:
        Number of jobs cleaned up
    """
    try:
        current_time = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        # Use ExpiresAtIndex for efficient querying
        response = get_fzip_jobs_table().query(
            IndexName='ExpiresAtIndex',
            KeyConditionExpression=Key('expiresAt').lt(current_time)
        )
        
        expired_jobs = response.get('Items', [])
        cleanup_count = 0
        
        # Delete expired jobs in batches
        with get_fzip_jobs_table().batch_writer() as batch:
            for job_item in expired_jobs:
                batch.delete_item(Key={'jobId': job_item['jobId']})
                cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} expired FZIP jobs")
            
        return cleanup_count
        
    except Exception as e:
        logger.error(f"Error cleaning up expired FZIP jobs: {str(e)}")
        return 0


