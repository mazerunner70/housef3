"""
Transaction database operations.

This module provides CRUD operations for transactions.
"""

import logging
import uuid
import operator
from functools import reduce
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union, Tuple
from boto3.dynamodb.conditions import Key, Attr

from models.transaction import Transaction
from .base import (
    tables,
    dynamodb_operation,
    retry_on_throttle,
    monitor_performance,
    NotFound,
    check_user_owns_resource,
)
from .helpers import batch_delete_items

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def checked_optional_transaction(transaction_id: Optional[uuid.UUID], user_id: str) -> Optional[Transaction]:
    """
    Check if transaction exists and user has access to it, allowing None.
    
    Args:
        transaction_id: ID of the transaction (or None)
        user_id: ID of the user requesting access
        
    Returns:
        Transaction object if found and authorized, None if transaction_id is None or not found
        
    Raises:
        NotAuthorized: If transaction exists but user doesn't own it
    """
    if not transaction_id:
        return None
    
    transaction = _get_transaction(transaction_id)
    if not transaction:
        return None
    
    check_user_owns_resource(transaction.user_id, user_id)
    return transaction


def checked_mandatory_transaction(transaction_id: uuid.UUID, user_id: str) -> Transaction:
    """
    Check if transaction exists and user has access to it.
    
    Args:
        transaction_id: ID of the transaction
        user_id: ID of the user requesting access
        
    Returns:
        Transaction object if found and authorized
        
    Raises:
        NotFound: If transaction doesn't exist
        NotAuthorized: If user doesn't own the transaction
    """
    if not transaction_id:
        raise NotFound("Transaction ID is required")
    
    transaction = checked_optional_transaction(transaction_id, user_id)
    if not transaction:
        raise NotFound("Transaction not found")
    
    return transaction


# ============================================================================
# Internal Getter (not exported)
# ============================================================================

def _get_transaction(transaction_id: uuid.UUID) -> Optional[Transaction]:
    """
    Retrieve a transaction by ID (no user validation).
    INTERNAL USE ONLY - external code should use checked_mandatory_transaction.
    
    Args:
        transaction_id: ID of the transaction
        
    Returns:
        Transaction object if found, None otherwise
    """
    table = tables.transactions
    if not table:
        logger.error("Transaction database not available")
        return None
    
    response = table.get_item(Key={'transactionId': str(transaction_id)})
    item = response.get('Item')
    
    if not item:
        return None
    
    return Transaction.from_dynamodb_item(item)


# ============================================================================
# Query Helper Functions
# ============================================================================

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
        key_condition = Key('status').eq('new')  # Non-duplicates have 'new' status
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


# ============================================================================
# CRUD Operations
# ============================================================================

def _list_file_transactions_internal(file_id: uuid.UUID) -> List[Transaction]:
    """
    Internal helper to list all transactions for a file (no auth check).
    INTERNAL USE ONLY - callers must verify authorization first.
    
    Args:
        file_id: The unique identifier of the file
        
    Returns:
        List of Transaction objects
    """
    response = tables.transactions.query(
        IndexName='FileIdIndex',
        KeyConditionExpression=Key('fileId').eq(str(file_id))
    )
    return [Transaction.from_dynamodb_item(item) for item in response.get('Items', [])]


def list_file_transactions(file_id: uuid.UUID, user_id: str) -> List[Transaction]:
    """
    List all transactions for a specific file.
    
    Args:
        file_id: The unique identifier of the file
        user_id: The user ID (for authorization)
        
    Returns:
        List of Transaction objects
        
    Raises:
        NotFound: If file doesn't exist
        NotAuthorized: If user doesn't own the file
    """
    # Import here to avoid circular dependency
    from .files import checked_mandatory_transaction_file
    
    # Check that user owns the file before listing its transactions
    _ = checked_mandatory_transaction_file(file_id, user_id)
    
    return _list_file_transactions_internal(file_id)


@monitor_performance(operation_type="query", warn_threshold_ms=1000)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("list_user_transactions")
def list_user_transactions(
    user_id: str, 
    limit: int = 50, 
    last_evaluated_key: Optional[Dict[str, Any]] = None,
    start_date_ts: Optional[int] = None,
    end_date_ts: Optional[int] = None,
    account_ids: Optional[List[uuid.UUID]] = None,
    category_ids: Optional[List[str]] = None,
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
    table = tables.transactions
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
        'Limit': limit,
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
    
    # Enhanced logging to diagnose DynamoDB pagination behavior
    scanned_count = response.get('ScannedCount', 0)
    returned_count = response.get('Count', 0)
    has_last_key = new_last_evaluated_key is not None
    
    logger.info(f"DynamoDB Query Result for user {user_id}: returned {items_in_current_response} items (requested: {limit}). "
               f"ScannedCount: {scanned_count}, Count: {returned_count}, HasLastEvaluatedKey: {has_last_key}")
    
    # Special logging for the problematic case: 0 scanned but LastEvaluatedKey present
    if scanned_count == 0 and has_last_key:
        logger.warning(f"PAGINATION ANOMALY: DynamoDB returned LastEvaluatedKey with ScannedCount=0 for user {user_id}. "
                      f"This is normal DynamoDB GSI behavior when no data exists in queried partitions. "
                      f"LastEvaluatedKey: {new_last_evaluated_key}")
    
    # Log filtering efficiency to help debug sparse data issues
    if scanned_count > 0:
        filter_efficiency = (returned_count / scanned_count) * 100
        logger.info(f"Filter efficiency: {filter_efficiency:.1f}% ({returned_count}/{scanned_count}) items passed filters")
    elif returned_count > 0:
        logger.info(f"No filtering occurred - all {returned_count} items returned directly from GSI")

    return transactions, new_last_evaluated_key, items_in_current_response


@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("create_transaction")
def create_transaction(transaction: Transaction):
    """
    Create a new transaction.
    
    Args:
        transaction: Transaction object to create
        
    Returns:
        The created Transaction object
    """
    # Save to DynamoDB
    tables.transactions.put_item(Item=transaction.to_dynamodb_item())
    return transaction


@monitor_performance(warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("delete_transactions_for_file")
def delete_transactions_for_file(file_id: uuid.UUID) -> int:
    """
    Delete all transactions associated with a file.
    
    Note: This is an internal helper function. Callers must verify
    authorization before calling this function.
    
    Args:
        file_id: The ID of the file whose transactions should be deleted
        
    Returns:
        Number of transactions deleted
    """
    # Get all transactions for the file (using internal helper, auth already checked by caller)
    transactions = _list_file_transactions_internal(file_id)
    
    if not transactions:
        return 0
    
    # Delete transactions using batch helper
    count = batch_delete_items(
        table=tables.transactions,
        items=transactions,
        key_extractor=lambda t: {'transactionId': str(t.transaction_id)}
    )
    
    logger.info(f"Deleted {count} transactions for file {str(file_id)}")
    return count


@monitor_performance(operation_type="query", warn_threshold_ms=1000)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("list_account_transactions")
def list_account_transactions(account_id: str, user_id: str, limit: int = 50, last_evaluated_key: Optional[Dict] = None) -> List[Transaction]:
    """
    List transactions for a specific account with pagination.
    
    Note: This function requires a GSI named 'AccountDateIndex' with:
        - Partition key: accountId
        - Sort key: date
        - Additional attributes: importOrder
    
    Args:
        account_id: The account ID to list transactions for
        user_id: The user ID (for authorization)
        limit: Maximum number of transactions to return
        last_evaluated_key: Key to start from for pagination
        
    Returns:
        List of Transaction objects sorted by date (ascending)
        
    Raises:
        NotFound: If account doesn't exist
        NotAuthorized: If user doesn't own the account
    """
    # Import here to avoid circular dependency
    from .accounts import checked_mandatory_account
    
    # Check that user owns the account before listing its transactions
    _ = checked_mandatory_account(uuid.UUID(account_id), user_id)
    
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
        
    response = tables.transactions.query(**query_params)
    
    # Convert items to Transaction objects
    transactions = [Transaction.from_dynamodb_item(item) for item in response.get('Items', [])]
    
    # Sort by import order within each date
    transactions.sort(key=lambda x: (x.date, x.import_order or 0))
        
    return transactions


@monitor_performance(warn_threshold_ms=2000)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("update_transaction_statuses_by_status")
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
    table = tables.transactions
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
                        'updatedAt': int(datetime.now(timezone.utc).timestamp() * 1000)
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


@monitor_performance(operation_type="query", warn_threshold_ms=200)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("get_transaction_by_account_and_hash")
def get_transaction_by_account_and_hash(account_id: Union[str, uuid.UUID], transaction_hash: int) -> Optional[Transaction]:
    """
    Retrieve a specific transaction by account ID and transaction hash.
    
    Args:
        account_id: The account ID
        transaction_hash: The transaction hash
        
    Returns:
        Transaction object if found, None otherwise
    """
    response = tables.transactions.query(
        IndexName='TransactionHashIndex', 
        KeyConditionExpression=Key('accountId').eq(str(account_id)) & Key('transactionHash').eq(transaction_hash)
    )
    if response.get('Items'):
        return Transaction.from_dynamodb_item(response['Items'][0])
    return None


@monitor_performance(warn_threshold_ms=200)
@dynamodb_operation("check_duplicate_transaction")
def check_duplicate_transaction(transaction: Transaction) -> bool: 
    """
    Check if a transaction already exists for the given account using numeric hash.
    
    Args:
        transaction: Transaction object
        
    Returns:
        bool: True if duplicate found, False otherwise
    """
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


@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("update_transaction")
def update_transaction(transaction: Transaction) -> None:
    """
    Update an existing transaction in DynamoDB.
    
    Args:
        transaction: Transaction object to update
    """
    tables.transactions.put_item(Item=transaction.to_dynamodb_item())


@monitor_performance(operation_type="query", warn_threshold_ms=200)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("get_first_transaction_date")
def get_first_transaction_date(account_id: Union[str, uuid.UUID]) -> Optional[int]:
    """
    Get the earliest transaction date for a specific account.
    Only considers transactions with status starting with 'new' (non-duplicates).
    
    Args:
        account_id: The account ID
        
    Returns:
        Transaction date as milliseconds since epoch, or None if no transactions found
    """
    # Query the earliest non-duplicate transaction for this account
    # The statusDate field is a composite key of format "status#timestamp"
    response = tables.transactions.query(
        IndexName='AccountStatusDateIndex',
        KeyConditionExpression=Key('accountId').eq(str(account_id)) & Key('statusDate').begins_with('new#'),
        Limit=1,
        ScanIndexForward=True  # Sort in ascending order to get earliest first
    )
    
    if response.get('Items'):
        return response['Items'][0].get('date')
    return None


@monitor_performance(operation_type="query", warn_threshold_ms=200)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("get_last_transaction_date")
def get_last_transaction_date(account_id: Union[str, uuid.UUID]) -> Optional[int]:
    """
    Get the most recent transaction date for a specific account.
    Only considers transactions with status starting with 'new' (non-duplicates).
    
    Args:
        account_id: The account ID
        
    Returns:
        Transaction date as milliseconds since epoch, or None if no transactions found
    """
    # Query the most recent non-duplicate transaction for this account
    # The statusDate field is a composite key of format "status#timestamp"
    response = tables.transactions.query(
        IndexName='AccountStatusDateIndex',
        KeyConditionExpression=Key('accountId').eq(str(account_id)) & Key('statusDate').begins_with('new#'),
        Limit=1,
        ScanIndexForward=False  # Sort in descending order to get most recent first
    )
    
    if response.get('Items'):
        return response['Items'][0].get('date')
    return None


@monitor_performance(operation_type="query", warn_threshold_ms=200)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("get_latest_transaction")
def get_latest_transaction(account_id: Union[str, uuid.UUID]) -> Optional[Transaction]:
    """
    Get the most recent transaction for a specific account.
    Only considers transactions with status starting with 'new' (non-duplicates).
    
    Args:
        account_id: The account ID
        
    Returns:
        Transaction object or None if no transactions found
    """
    # Query the most recent non-duplicate transaction for this account
    # The statusDate field is a composite key of format "status#timestamp"
    response = tables.transactions.query(
        IndexName='AccountStatusDateIndex',
        KeyConditionExpression=Key('accountId').eq(str(account_id)) & Key('statusDate').begins_with('new#'),
        Limit=1,
        ScanIndexForward=False  # Sort in descending order to get most recent first
    )
    logger.info(f"DB: get_latest_transaction response: {response}")
    
    if response.get('Items'):
        return Transaction.from_dynamodb_item(response['Items'][0])
    return None

