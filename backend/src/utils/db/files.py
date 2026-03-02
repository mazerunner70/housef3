"""
File and FileMap database operations.

This module provides CRUD operations for transaction files and file maps.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from boto3.dynamodb.conditions import Key

from models import TransactionFile
from models.transaction_file import TransactionFileUpdate
from models.file_map import FileMap
from .base import (
    tables,
    dynamodb_operation,
    retry_on_throttle,
    monitor_performance,
    NotFound,
    check_user_owns_resource,
)

logger = logging.getLogger(__name__)


# ============================================================================
# TransactionFile Helper Functions
# ============================================================================

def checked_optional_transaction_file(file_id: Optional[uuid.UUID], user_id: str) -> Optional[TransactionFile]:
    """
    Check if file exists and user has access to it, allowing None.
    
    Args:
        file_id: ID of the file (or None)
        user_id: ID of the user requesting access
        
    Returns:
        TransactionFile object if found and authorized, None if file_id is None or not found
        
    Raises:
        NotAuthorized: If file exists but user doesn't own it
    """
    if not file_id:
        return None
    
    file = _get_transaction_file(file_id)
    if not file:
        return None
    
    check_user_owns_resource(file.user_id, user_id)
    return file


def checked_mandatory_transaction_file(file_id: uuid.UUID, user_id: str) -> TransactionFile:
    """
    Check if file exists and user has access to it.
    
    Args:
        file_id: ID of the file
        user_id: ID of the user requesting access
        
    Returns:
        TransactionFile object if found and authorized
        
    Raises:
        NotFound: If file doesn't exist
        NotAuthorized: If user doesn't own the file
    """
    if not file_id:
        raise NotFound("File ID is required")
    
    file = checked_optional_transaction_file(file_id, user_id)
    if not file:
        raise NotFound("File not found")
    
    return file


# ============================================================================
# Internal Getters (not exported)
# ============================================================================

def _get_transaction_file(file_id: uuid.UUID) -> Optional[TransactionFile]:
    """
    Retrieve a transaction file by ID (no user validation).
    INTERNAL USE ONLY - external code should use checked_mandatory_transaction_file.
    
    Args:
        file_id: The unique identifier of the file
        
    Returns:
        TransactionFile object if found, None otherwise
    """
    response = tables.files.get_item(Key={'fileId': str(file_id)})
    
    if 'Item' in response:
        logger.info(f"3 {response['Item']}")
        tfd = TransactionFile.from_dynamodb_item(response['Item'])
        logger.info(f"2exact type {type(tfd.file_format)} {tfd.file_format}")
        return tfd
    return None


# ============================================================================
# TransactionFile CRUD Operations
# ============================================================================


@monitor_performance(operation_type="query", warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("list_account_files")
def list_account_files(account_id: uuid.UUID, user_id: str) -> List[TransactionFile]:
    """
    List all files for a specific account.
    
    Args:
        account_id: The account's unique identifier
        user_id: The user ID (for authorization)
        
    Returns:
        List of TransactionFile objects
        
    Raises:
        NotFound: If account doesn't exist
        NotAuthorized: If user doesn't own the account
    """
    # Import here to avoid circular dependency
    from .accounts import checked_mandatory_account
    
    # Check that user owns the account before listing its files
    _ = checked_mandatory_account(account_id, user_id)
    
    # Query using GSI for accountId
    response = tables.files.query(
        IndexName='AccountIdIndex',
        KeyConditionExpression=Key('accountId').eq(str(account_id))
    )
    logger.info(f"1 {response['Items']}")
    files = []
    for item in response.get('Items', []):
        files.append(TransactionFile.from_dynamodb_item(item))
        
    return files


@monitor_performance(operation_type="query", warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("list_user_files")
def list_user_files(user_id: str) -> List[TransactionFile]:
    """
    List all files for a specific user.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        List of TransactionFile objects
    """
    # Query using GSI for userId
    response = tables.files.query(
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


@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("create_transaction_file")
def create_transaction_file(transaction_file: TransactionFile):
    """
    Create a new transaction file record.
    
    Args:
        transaction_file: TransactionFile object to create
    """
    # Save to DynamoDB
    tables.files.put_item(Item=transaction_file.to_dynamodb_item())


@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("update_transaction_file")
def update_transaction_file(file_id: uuid.UUID, user_id: str, updates: Dict[str, Any]):
    """
    Update a transaction file record in DynamoDB.
    
    Args:
        file_id: The unique identifier of the file
        user_id: The user ID (for authorization)
        updates: Dictionary of fields to update with their new values
    """
    transaction_file = checked_mandatory_transaction_file(file_id, user_id)
    
    # Create TransactionFileUpdate DTO
    update_dto = TransactionFileUpdate(**updates)
    
    # Use the model's method to update details
    transaction_file.update_with_data(update_dto)
    
    tables.files.put_item(Item=transaction_file.to_dynamodb_item())


@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("update_transaction_file_object")
def update_transaction_file_object(transaction_file: TransactionFile):
    """
    Update a transaction file object in DynamoDB.
    
    Args:
        transaction_file: TransactionFile object with updated details
    """
    tables.files.put_item(Item=transaction_file.to_dynamodb_item())


@monitor_performance(warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("delete_transaction_file")
def delete_transaction_file(file_id: uuid.UUID, user_id: str) -> bool:
    """
    Delete a transaction file and all its associated transactions.
    
    Args:
        file_id: The unique identifier of the file to delete
        user_id: The ID of the user requesting the deletion
        
    Returns:
        True if deleted successfully
    """
    # Import here to avoid circular dependency
    from .transactions import delete_transactions_for_file
    
    # Check if the file exists and user owns it
    _ = checked_mandatory_transaction_file(file_id, user_id)
    
    # First delete all associated transactions
    transactions_deleted = delete_transactions_for_file(file_id)
    logger.info(f"Deleted {transactions_deleted} transactions for file {str(file_id)}")
    
    # Then delete the file metadata
    tables.files.delete_item(Key={'fileId': str(file_id)})
    logger.info(f"Deleted file metadata for {str(file_id)}")
    
    return True


@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("delete_file_metadata")
def delete_file_metadata(file_id: uuid.UUID, user_id: str) -> bool:
    """
    Delete a file metadata record from the files table.
    
    Args:
        file_id: The ID of the file to delete
        user_id: The user ID (for authorization)
        
    Returns:
        True if successful
        
    Raises:
        NotFound: If file doesn't exist
        NotAuthorized: If user doesn't own the file
    """
    # Check ownership before deleting
    _ = checked_mandatory_transaction_file(file_id, user_id)
    
    tables.files.delete_item(Key={'fileId': str(file_id)})
    logger.info(f"Deleted file metadata for {str(file_id)}")
    return True


@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("update_file_account_id")
def update_file_account_id(file_id: str, account_id: str, user_id: str) -> None:
    """
    Update the accountId of a file in the files table.
    
    Args:
        file_id: The unique identifier of the file
        account_id: The account ID to associate with the file
        user_id: The user ID (for authorization)
        
    Raises:
        NotFound: If file doesn't exist
        NotAuthorized: If user doesn't own the file
    """
    # Check ownership before updating
    _ = checked_mandatory_transaction_file(uuid.UUID(file_id), user_id)
    
    table = tables.files
    update_expression = "SET accountId = :accountId, updatedAt = :updatedAt"
    expression_attribute_values = {
        ":accountId": str(account_id),
        ":updatedAt": int(datetime.now(timezone.utc).timestamp() * 1000)
    }
    table.update_item(
        Key={'fileId': str(file_id)},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values
    )


@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("update_file_field_map")
def update_file_field_map(file_id: str, field_map_id: str, user_id: str) -> None:
    """
    Update the fieldMapId of a file in the files table.
    
    Args:
        file_id: The unique identifier of the file
        field_map_id: The field map ID to associate with the file
        user_id: The user ID (for authorization)
        
    Raises:
        NotFound: If file doesn't exist
        NotAuthorized: If user doesn't own the file
    """
    # Check ownership before updating
    _ = checked_mandatory_transaction_file(uuid.UUID(file_id), user_id)
    
    table = tables.files
    update_expression = "SET fieldMapId = :fieldMapId, updatedAt = :updatedAt"
    expression_attribute_values = {
        ":fieldMapId": str(field_map_id),
        ":updatedAt": int(datetime.now(timezone.utc).timestamp() * 1000)
    }
    table.update_item(
        Key={'fileId': str(file_id)},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values
    )


# ============================================================================
# FileMap Helper Functions
# ============================================================================

def checked_optional_file_map(file_map_id: Optional[uuid.UUID], user_id: str) -> Optional[FileMap]:
    """
    Check if file map exists and user has access to it, allowing None.
    
    Args:
        file_map_id: ID of the file map (or None)
        user_id: ID of the user requesting access
        
    Returns:
        FileMap object if found and authorized, None if file_map_id is None or not found
        
    Raises:
        NotAuthorized: If file map exists but user doesn't own it
    """
    if not file_map_id:
        return None
    
    file_map = _get_file_map(file_map_id)
    if not file_map:
        return None
    
    check_user_owns_resource(file_map.user_id, user_id)
    return file_map


def checked_mandatory_file_map(file_map_id: Optional[uuid.UUID], user_id: str) -> FileMap:
    """
    Check if file map exists and user has access to it.
    
    Args:
        file_map_id: ID of the file map
        user_id: ID of the user requesting access
        
    Returns:
        FileMap object if found and authorized
        
    Raises:
        NotFound: If file_map_id is None or file map doesn't exist
        NotAuthorized: If user doesn't own the file map
    """
    if not file_map_id:
        raise NotFound("FileMap ID is required")
    
    file_map = checked_optional_file_map(file_map_id, user_id)
    if not file_map:
        raise NotFound("File map not found")
    
    return file_map


# ============================================================================
# FileMap CRUD Operations
# ============================================================================

@monitor_performance(warn_threshold_ms=200)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("_get_file_map")
def _get_file_map(file_map_id: Optional[uuid.UUID] = None) -> Optional[FileMap]:
    """
    Retrieve a file map by ID (no user validation).
    INTERNAL USE ONLY - external code should use checked_mandatory_file_map.
    
    Args:
        file_map_id: The unique identifier of the file map
        
    Returns:
        FileMap object if found, None otherwise
    """
    if not file_map_id:
        return None
    
    table = tables.file_maps
    if not table:
        logger.error("File maps table not initialized.")
        return None
    response = table.get_item(Key={'fileMapId': str(file_map_id)})

    if 'Item' in response:
        return FileMap.from_dynamodb_item(response['Item'])
    return None


@monitor_performance(warn_threshold_ms=300)
@dynamodb_operation("get_account_default_file_map")
def get_account_default_file_map(account_id: uuid.UUID, user_id: str) -> Optional[FileMap]:
    """
    Get the default file map for an account.
    
    Args:
        account_id: ID of the account
        user_id: ID of the user (for authorization)
        
    Returns:
        FileMap instance if found, None otherwise
        
    Raises:
        NotFound: If account doesn't exist
        NotAuthorized: If user doesn't own the account
    """
    # Import here to avoid circular dependency
    from .accounts import checked_mandatory_account
    
    # Get the account record with authorization check
    account = checked_mandatory_account(account_id, user_id)
        
    # Check for default field map
    default_file_map_id = account.default_file_map_id 
    if not default_file_map_id:
        return None
        
    # Get the field map (no need to check ownership since it's referenced by the account)
    return _get_file_map(default_file_map_id)


@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("create_file_map")
def create_file_map(file_map: FileMap) -> None:
    """
    Create a new file map.
    
    Args:
        file_map: The FileMap object to create
    """
    tables.file_maps.put_item(Item=file_map.to_dynamodb_item())
    logger.info(f"Successfully created file map {str(file_map.file_map_id)}")


@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("update_file_map")
def update_file_map(file_map: FileMap) -> None:
    """
    Update an existing file map.
    
    Args:
        file_map: The FileMap object with updated details
    """
    tables.file_maps.put_item(Item=file_map.to_dynamodb_item())
    logger.info(f"Successfully updated file map {str(file_map.file_map_id)}")


@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("delete_file_map")
def delete_file_map(file_map_id: uuid.UUID, user_id: str) -> bool:
    """
    Delete a file map by ID.
    
    Args:
        file_map_id: ID of the file map to delete
        user_id: ID of the user (for authorization)
        
    Returns:
        True if successful
        
    Raises:
        NotFound: If file map doesn't exist
        NotAuthorized: If user doesn't own the file map
    """
    # Check ownership before deleting
    _ = checked_mandatory_file_map(file_map_id, user_id)
    
    tables.file_maps.delete_item(
        Key={'fileMapId': str(file_map_id)}
    )
    return True


@monitor_performance(operation_type="query", warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("list_file_maps_by_user")
def list_file_maps_by_user(user_id: str) -> List[FileMap]:
    """
    List all file maps for a specific user.
    
    Args:
        user_id: ID of the user
        
    Returns:
        List of FileMap instances
    """
    response = tables.file_maps.query(
        IndexName='UserIdIndex',
        KeyConditionExpression=Key('userId').eq(user_id)
    )
    return [FileMap.from_dynamodb_item(item) for item in response.get('Items', [])]


@monitor_performance(operation_type="query", warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("list_account_file_maps")
def list_account_file_maps(account_id: str, user_id: str) -> List[FileMap]:
    """
    List all file maps for a specific account.
    
    Args:
        account_id: The account's unique identifier
        user_id: The user ID (for authorization)
        
    Returns:
        List of FileMap objects
        
    Raises:
        NotFound: If account doesn't exist
        NotAuthorized: If user doesn't own the account
    """
    # Import here to avoid circular dependency
    from .accounts import checked_mandatory_account
    
    # Check that user owns the account before listing its file maps
    _ = checked_mandatory_account(uuid.UUID(account_id), user_id)
    
    # Query using GSI for accountId
    response = tables.file_maps.query(
        IndexName='AccountIdIndex',
        KeyConditionExpression=Key('accountId').eq(str(account_id))
    )
    return [FileMap.from_dynamodb_item(item) for item in response.get('Items', [])]

