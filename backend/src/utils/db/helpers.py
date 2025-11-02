"""
Helper functions for database operations.

This module provides:
- Batch operation helpers
- Pagination helpers
- UUID conversion helpers
- Query building helpers
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union, Tuple, Callable, TypeVar, Sequence
from decimal import Decimal

logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar('T')


# ============================================================================
# UUID Conversion Helpers
# ============================================================================

def to_db_id(id_value: Union[str, uuid.UUID, None]) -> Optional[str]:
    """
    Convert UUID to string for DynamoDB operations.
    
    DynamoDB doesn't have a native UUID type, so we store as strings.
    This helper ensures consistent conversion.
    
    Args:
        id_value: UUID, string, or None
    
    Returns:
        String representation or None
    
    Example:
        key = {'accountId': to_db_id(account_id)}
    """
    if id_value is None:
        return None
    return str(id_value)


def from_db_id(id_value: Optional[str]) -> Optional[uuid.UUID]:
    """
    Convert string from DynamoDB to UUID.
    
    Args:
        id_value: String representation of UUID or None
    
    Returns:
        UUID object or None
    
    Raises:
        ValueError: If string is not a valid UUID
    
    Example:
        account_id = from_db_id(item.get('accountId'))
    """
    if id_value is None:
        return None
    try:
        return uuid.UUID(id_value)
    except ValueError:
        logger.error(f"Invalid UUID string: {id_value}")
        raise


def to_db_ids(id_list: Sequence[Union[str, uuid.UUID]]) -> List[str]:
    """
    Convert list of UUIDs to list of strings.
    
    Args:
        id_list: Sequence of UUIDs or strings
        
    Returns:
        List of string representations
    """
    return [str(id_val) for id_val in id_list]


def from_db_ids(id_list: List[str]) -> List[uuid.UUID]:
    """
    Convert list of strings to list of UUIDs.
    
    Args:
        id_list: List of UUID strings
        
    Returns:
        List of UUID objects
        
    Raises:
        ValueError: If any string is not a valid UUID
    """
    return [uuid.UUID(id_val) for id_val in id_list]


# ============================================================================
# Batch Operation Helpers
# ============================================================================

def batch_delete_items(
    table: Any,
    items: List[Any],
    key_extractor: Callable[[Any], Dict[str, str]],
    batch_size: int = 25
) -> int:
    """
    Delete items in batches respecting DynamoDB limits.
    
    Args:
        table: DynamoDB table resource
        items: List of items to delete (can be models or dicts)
        key_extractor: Function to extract key dict from item
        batch_size: Batch size (DynamoDB limit is 25)
    
    Returns:
        Number of items deleted
    
    Example:
        # Delete transactions
        deleted_count = batch_delete_items(
            table=tables.transactions,
            items=transactions,
            key_extractor=lambda t: {'transactionId': str(t.transaction_id)}
        )
    """
    if not items:
        logger.debug("No items to delete")
        return 0
    
    count = 0
    
    # Process in batches
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        
        with table.batch_writer() as writer:
            for item in batch:
                writer.delete_item(Key=key_extractor(item))
                count += 1
    
    logger.info(f"Batch deleted {count} items from {table.table_name}")
    return count


def batch_write_items(
    table: Any,
    items: List[Dict[str, Any]],
    batch_size: int = 25
) -> int:
    """
    Write items in batches respecting DynamoDB limits.
    
    Args:
        table: DynamoDB table resource
        items: List of item dicts to write
        batch_size: Batch size (DynamoDB limit is 25)
    
    Returns:
        Number of items written
    
    Example:
        # Write analytics data
        written_count = batch_write_items(
            table=tables.analytics_data,
            items=[data.to_dynamodb_item() for data in analytics_list]
        )
    """
    if not items:
        logger.debug("No items to write")
        return 0
    
    count = 0
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        
        with table.batch_writer() as writer:
            for item in batch:
                writer.put_item(Item=item)
                count += 1
    
    logger.info(f"Batch wrote {count} items to {table.table_name}")
    return count


def batch_update_items(
    table: Any,
    items: List[Any],
    updater: Callable[[Any], Dict[str, Any]],
    batch_size: int = 25
) -> int:
    """
    Update items in batches.
    
    Note: DynamoDB batch_writer doesn't support updates directly,
    so this uses put_item (overwrites existing items).
    
    Args:
        table: DynamoDB table resource
        items: List of items to update
        updater: Function that takes an item and returns updated dict
        batch_size: Batch size
    
    Returns:
        Number of items updated
    
    Example:
        # Update transaction statuses
        updated_count = batch_update_items(
            table=tables.transactions,
            items=transactions,
            updater=lambda t: {
                **t.to_dynamodb_item(),
                'status': 'processed',
                'updatedAt': current_timestamp()
            }
        )
    """
    if not items:
        logger.debug("No items to update")
        return 0
    
    count = 0
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        
        with table.batch_writer() as writer:
            for item in batch:
                updated_item = updater(item)
                writer.put_item(Item=updated_item)
                count += 1
    
    logger.info(f"Batch updated {count} items in {table.table_name}")
    return count


# ============================================================================
# Pagination Helper
# ============================================================================

def paginated_query(
    table: Any,
    query_params: Dict[str, Any],
    max_items: Optional[int] = None,
    transform: Optional[Callable[[Dict], T]] = None
) -> Tuple[List[T], Optional[Dict[str, Any]]]:
    """
    Execute paginated DynamoDB query and return all items.
    
    Args:
        table: DynamoDB table resource
        query_params: Query parameters (KeyConditionExpression, etc.)
        max_items: Maximum items to return (None for all)
        transform: Optional function to transform each item
    
    Returns:
        Tuple of (items, last_evaluated_key)
    
    Example:
        from boto3.dynamodb.conditions import Key
        
        items, last_key = paginated_query(
            table=tables.transactions,
            query_params={
                'IndexName': 'UserIdIndex',
                'KeyConditionExpression': Key('userId').eq(user_id),
                'Limit': 100
            },
            transform=Transaction.from_dynamodb_item
        )
    """
    items: List[T] = []
    items_collected = 0
    current_params = query_params.copy()
    last_evaluated_key = None
    
    while True:
        response = table.query(**current_params)
        batch = response.get('Items', [])
        
        # Transform items if transformer provided
        if transform:
            batch = [transform(item) for item in batch]
        
        items.extend(batch)
        items_collected += len(batch)
        
        # Check if we've collected enough items
        if max_items and items_collected >= max_items:
            items = items[:max_items]
            last_evaluated_key = response.get('LastEvaluatedKey')
            break
        
        # Check for more pages
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break
        
        current_params['ExclusiveStartKey'] = last_evaluated_key
    
    logger.debug(f"Paginated query returned {len(items)} items")
    return items, last_evaluated_key


def paginated_scan(
    table: Any,
    scan_params: Dict[str, Any],
    max_items: Optional[int] = None,
    transform: Optional[Callable[[Dict], T]] = None
) -> Tuple[List[T], Optional[Dict[str, Any]]]:
    """
    Execute paginated DynamoDB scan and return all items.
    
    Args:
        table: DynamoDB table resource
        scan_params: Scan parameters (FilterExpression, etc.)
        max_items: Maximum items to return (None for all)
        transform: Optional function to transform each item
    
    Returns:
        Tuple of (items, last_evaluated_key)
    
    Example:
        items, last_key = paginated_scan(
            table=tables.fzip_jobs,
            scan_params={
                'FilterExpression': Attr('status').eq('expired')
            },
            transform=FZIPJob.from_dynamodb_item
        )
    """
    items: List[T] = []
    items_collected = 0
    current_params = scan_params.copy()
    last_evaluated_key = None
    
    while True:
        response = table.scan(**current_params)
        batch = response.get('Items', [])
        
        # Transform items if transformer provided
        if transform:
            batch = [transform(item) for item in batch]
        
        items.extend(batch)
        items_collected += len(batch)
        
        # Check if we've collected enough items
        if max_items and items_collected >= max_items:
            items = items[:max_items]
            last_evaluated_key = response.get('LastEvaluatedKey')
            break
        
        # Check for more pages
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break
        
        current_params['ExclusiveStartKey'] = last_evaluated_key
    
    logger.debug(f"Paginated scan returned {len(items)} items")
    return items, last_evaluated_key


# ============================================================================
# Update Expression Builder
# ============================================================================

def build_update_expression(
    updates: Dict[str, Any],
    timestamp_field: Optional[str] = 'updatedAt',
    remove_fields: Optional[List[str]] = None
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    """
    Build DynamoDB UpdateExpression from update dictionary.
    
    Args:
        updates: Dictionary of field names to new values
        timestamp_field: Name of timestamp field to auto-update (None to skip)
        remove_fields: List of field names to remove (optional)
    
    Returns:
        Tuple of (update_expression, expression_attribute_names, expression_attribute_values)
    
    Example:
        expr, names, values = build_update_expression(
            updates={'name': 'New Name', 'balance': Decimal('1000.00')},
            remove_fields=['oldField']
        )
        table.update_item(
            Key={'accountId': account_id},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values
        )
    """
    if not updates and not remove_fields:
        raise ValueError("Either updates or remove_fields must be provided")
    
    set_parts: List[str] = []
    remove_parts: List[str] = []
    expr_attr_names: Dict[str, str] = {}
    expr_attr_values: Dict[str, Any] = {}
    
    # Process SET operations
    for key, value in updates.items():
        # Use attribute names to handle reserved words
        # Replace hyphens with underscores for placeholder names
        safe_key = key.replace('-', '_').replace('.', '_')
        set_parts.append(f"#{safe_key} = :{safe_key}")
        expr_attr_names[f"#{safe_key}"] = key
        expr_attr_values[f":{safe_key}"] = value
    
    # Add timestamp if specified
    if timestamp_field:
        safe_timestamp = timestamp_field.replace('-', '_').replace('.', '_')
        set_parts.append(f"#{safe_timestamp} = :{safe_timestamp}")
        expr_attr_names[f"#{safe_timestamp}"] = timestamp_field
        expr_attr_values[f":{safe_timestamp}"] = int(
            datetime.now(timezone.utc).timestamp() * 1000
        )
    
    # Process REMOVE operations
    if remove_fields:
        for field in remove_fields:
            safe_field = field.replace('-', '_').replace('.', '_')
            remove_parts.append(f"#{safe_field}")
            expr_attr_names[f"#{safe_field}"] = field
    
    # Build the complete expression
    expression_parts = []
    if set_parts:
        expression_parts.append("SET " + ", ".join(set_parts))
    if remove_parts:
        expression_parts.append("REMOVE " + ", ".join(remove_parts))
    
    update_expression = " ".join(expression_parts)
    
    return update_expression, expr_attr_names, expr_attr_values


def build_condition_expression(
    conditions: Dict[str, Any],
    operator: str = "AND"
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    """
    Build DynamoDB ConditionExpression for conditional writes.
    
    Args:
        conditions: Dictionary of field names to expected values
        operator: Logical operator to join conditions ("AND" or "OR")
    
    Returns:
        Tuple of (condition_expression, expression_attribute_names, expression_attribute_values)
    
    Example:
        expr, names, values = build_condition_expression(
            conditions={'version': 5, 'status': 'active'}
        )
        table.update_item(
            Key={'accountId': account_id},
            UpdateExpression=update_expr,
            ConditionExpression=expr,
            ExpressionAttributeNames={**update_names, **names},
            ExpressionAttributeValues={**update_values, **values}
        )
    """
    if not conditions:
        raise ValueError("At least one condition must be provided")
    
    if operator.upper() not in ("AND", "OR"):
        raise ValueError("Operator must be 'AND' or 'OR'")
    
    condition_parts: List[str] = []
    expr_attr_names: Dict[str, str] = {}
    expr_attr_values: Dict[str, Any] = {}
    
    for key, value in conditions.items():
        # Use attribute names to handle reserved words
        safe_key = key.replace('-', '_').replace('.', '_')
        condition_parts.append(f"#{safe_key} = :{safe_key}")
        expr_attr_names[f"#{safe_key}"] = key
        expr_attr_values[f":{safe_key}"] = value
    
    condition_expression = f" {operator.upper()} ".join(condition_parts)
    
    return condition_expression, expr_attr_names, expr_attr_values


# ============================================================================
# Timestamp Helpers
# ============================================================================

def current_timestamp() -> int:
    """
    Get current timestamp in milliseconds (DynamoDB timestamp format).
    
    Returns:
        Current UTC timestamp in milliseconds
    """
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def timestamp_from_datetime(dt: datetime) -> int:
    """
    Convert datetime to DynamoDB timestamp (milliseconds).
    
    Args:
        dt: Datetime object (will be converted to UTC if naive)
        
    Returns:
        Timestamp in milliseconds
    """
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def datetime_from_timestamp(ts: int) -> datetime:
    """
    Convert DynamoDB timestamp (milliseconds) to datetime.
    
    Args:
        ts: Timestamp in milliseconds
        
    Returns:
        UTC datetime object
    """
    return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)


# ============================================================================
# Decimal Conversion Helpers (for DynamoDB number types)
# ============================================================================

def decimal_to_float(value: Any) -> Any:
    """
    Recursively convert Decimal values to float in nested structures.
    
    DynamoDB stores numbers as Decimal. This helper converts them to float
    for JSON serialization or other use cases.
    
    Args:
        value: Value to convert (can be nested dict/list)
        
    Returns:
        Value with all Decimals converted to float
    """
    if isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, dict):
        return {k: decimal_to_float(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [decimal_to_float(item) for item in value]
    else:
        return value


def float_to_decimal(value: Any) -> Any:
    """
    Recursively convert float values to Decimal in nested structures.
    
    DynamoDB requires numbers to be Decimal. This helper converts floats
    to Decimal for storage.
    
    Args:
        value: Value to convert (can be nested dict/list)
        
    Returns:
        Value with all floats converted to Decimal
    """
    if isinstance(value, float):
        return Decimal(str(value))
    elif isinstance(value, dict):
        return {k: float_to_decimal(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [float_to_decimal(item) for item in value]
    else:
        return value

