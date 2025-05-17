"""
Utility functions for database operations.
"""
import os
import logging
import traceback
import boto3
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from botocore.exceptions import ClientError
from decimal import Decimal

from models import (
    Account, 
    TransactionFile,
    validate_account_data,
    validate_transaction_file_data,
    AccountType,
    Currency
)
from models.transaction import Transaction
from boto3.dynamodb.conditions import Key, Attr
from models.file_map import FileMap
from utils.auth import checked_mandatory_account, checked_mandatory_transaction_file
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

# Initialize table resources lazily
_accounts_table = None
_files_table = None
_transactions_table = None
_file_maps_table = None

def get_accounts_table() -> Any:
    """Get the accounts table resource, initializing it if needed."""
    global _accounts_table
    if _accounts_table is None and ACCOUNTS_TABLE:
        _accounts_table = dynamodb.Table(ACCOUNTS_TABLE)
    return _accounts_table

def get_files_table() -> Any:
    """Get the files table resource, initializing it if needed."""
    global _files_table
    if _files_table is None and FILES_TABLE:
        _files_table = dynamodb.Table(FILES_TABLE)
    return _files_table

def get_transactions_table() -> Any:
    """Get the transactions table resource, initializing it if needed."""
    global _transactions_table
    if _transactions_table is None and TRANSACTIONS_TABLE:
        _transactions_table = dynamodb.Table(TRANSACTIONS_TABLE)
    return _transactions_table

def get_file_maps_table() -> Any:
    """Get the file maps table resource, initializing it if needed."""
    global _file_maps_table
    if _file_maps_table is None and FILE_MAPS_TABLE:
        _file_maps_table = dynamodb.Table(FILE_MAPS_TABLE)
    return _file_maps_table

def get_account(account_id: str) -> Optional[Account]:
    """
    Retrieve an account by ID.
    
    Args:
        account_id: The unique identifier of the account
        
    Returns:
        Account object if found, None otherwise
    """
    try:
        response = get_accounts_table().get_item(Key={'accountId': account_id})
        
        if 'Item' in response:
            return Account.from_dict(response['Item'])
        return None
    except ClientError as e:
        logger.error(f"Error retrieving account {account_id}: {str(e)}")
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
            accounts.append(Account.from_dict(item))
            
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
    get_accounts_table().put_item(Item=account.to_dict())




def update_account(account_id: str, user_id: str, update_data: Dict[str, Any]) -> Account:
    """
    Update an existing account.
    
    Args:
        account_id: The unique identifier of the account to update
        update_data: Dictionary containing fields to update
        
    Returns:
        Updated Account object
    """
    # Retrieve the existing account
    account = checked_mandatory_account(account_id, user_id)
    
    # Convert enum string values to actual enum types
    if 'accountType' in update_data and isinstance(update_data['accountType'], str):
        update_data['accountType'] = AccountType(update_data['accountType'])
        
    if 'currency' in update_data and isinstance(update_data['currency'], str):
        update_data['currency'] = Currency(update_data['currency'])
    
    # Update fields
    update_data_snake_case = {}
    field_mapping = {
        'accountName': 'account_name',
        'accountType': 'account_type',
        'institution': 'institution',
        'balance': 'balance',
        'currency': 'currency',
        'notes': 'notes',
        'isActive': 'is_active',
        'defaultFieldMapId': 'default_field_map_id'
    }
    
    for key, value in update_data.items():
        if key in field_mapping:
            update_data_snake_case[field_mapping[key]] = value
        else:
            raise ValueError(f"Skipping update for field {key}")
    
    account.update(**update_data_snake_case)
    account.validate()
    
    # Save updates to DynamoDB
    get_accounts_table().put_item(Item=account.to_dict())
    
    return account



def delete_account(account_id: str) -> bool:
    """
    Delete an account and handle any associated files.
    
    Args:
        account_id: The unique identifier of the account to delete
        
    Returns:
        True if deleted successfully
    """
    try:
        # Check if the account exists
        account = get_account(account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")
        
        # Get all files associated with this account
        associated_files = list_account_files(account_id)
        logger.info(f"Found {len(associated_files)} files associated with account {account_id}")
        
        # Delete each associated file and its transactions
        for file in associated_files:
            try:
                # Delete the file and its transactions
                delete_transaction_file(file.file_id)
                logger.info(f"Deleted file {file.file_id} and its transactions")
            except Exception as file_error:
                logger.error(f"Error deleting file {file.file_id}: {str(file_error)}")
                # Continue with other files
        
        # Delete the account
        get_accounts_table().delete_item(Key={'accountId': account_id})
        logger.info(f"Account {account_id} deleted successfully")
        
        return True
    except ClientError as e:
        logger.error(f"Error deleting account {account_id}: {str(e)}")
        raise


def get_transaction_file(file_id: str) -> Optional[TransactionFile]:
    """
    Retrieve a transaction file by ID.
    
    Args:
        file_id: The unique identifier of the file
        
    Returns:
        TransactionFile object if found, None otherwise
    """
    try:
        response = get_files_table().get_item(Key={'fileId': file_id})
        
        if 'Item' in response:
            return TransactionFile.from_dict(response['Item'])
        return None
    except ClientError as e:
        logger.error(f"Error retrieving file {file_id}: {str(e)}")
        raise


def list_account_files(account_id: str) -> List[TransactionFile]:
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
            KeyConditionExpression=Key('accountId').eq(account_id)
        )
        
        files = []
        for item in response.get('Items', []):
            files.append(TransactionFile.from_dict(item))
            
        return files
    except ClientError as e:
        logger.error(f"Error listing files for account {account_id}: {str(e)}")
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
            files.append(TransactionFile.from_dict(item))
            
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
        # Validate the input data
        validate_transaction_file_data(transaction_file)
    
        
        # Save to DynamoDB
        get_files_table().put_item(Item=transaction_file.to_dict())
        
    except ValueError as e:
        logger.error(f"Validation error creating file: {str(e)}")
        #log stack trace
        logger.error(traceback.format_exc())
        raise
    except ClientError as e:
        logger.error(f"Error creating file: {str(e)}")        
        logger.error(traceback.format_exc())
        raise


def update_transaction_file(file_id: str, user_id: str, updates: Dict[str, Any]):
    """
    Update a transaction file record in DynamoDB.
    
    Args:
        file_id: The unique identifier of the file
        updates: Dictionary of fields to update with their new values
        
    Returns:
        bool: True if successful, False otherwise
    """

    transaction_file = checked_mandatory_transaction_file(file_id, user_id)
    transaction_file.update(**updates)
    transaction_file.validate()
    get_files_table().put_item(Item=transaction_file.to_dict())

def delete_transaction_file(file_id: str) -> bool:
    """
    Delete a transaction file and all its associated transactions.
    
    Args:
        file_id: The unique identifier of the file to delete
        
    Returns:
        True if deleted successfully
    """
    try:
        # Check if the file exists
        file = get_transaction_file(file_id)
        if not file:
            raise ValueError(f"File {file_id} not found")
        
        # First delete all associated transactions
        transactions_deleted = delete_transactions_for_file(file_id)
        logger.info(f"Deleted {transactions_deleted} transactions for file {file_id}")
        
        # Then delete the file metadata
        get_files_table().delete_item(Key={'fileId': file_id})
        logger.info(f"Deleted file metadata for {file_id}")
        
        return True
    except ClientError as e:
        logger.error(f"Error deleting file {file_id}: {str(e)}")
        raise


def list_file_transactions(file_id: str) -> List[Transaction]:
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
            KeyConditionExpression=Key('fileId').eq(file_id)
        )
        return [Transaction.from_dict(item) for item in response.get('Items', [])]
    except ClientError as e:
        logger.error(f"Error listing transactions for file {file_id}: {str(e)}")
        raise


def list_user_transactions(user_id: str) -> List[Transaction]:
    """
    List all transactions for a specific user using the UserIdIndex GSI.
    
    Args:
        user_id: The ID of the user whose transactions to retrieve
        
    Returns:
        List of Transaction objects
        
    Raises:
        ClientError if the query fails
    """
    try:
        response = get_transactions_table().query(
            IndexName='UserIdIndex',
            KeyConditionExpression=Key('userId').eq(user_id)
        )
        
        transactions = []
        for item in response.get('Items', []):
            transactions.append(Transaction.from_dict(item))
        
        return transactions
            
    except ClientError as e:
        logger.error(f"Error querying transactions by user: {str(e)}")
        raise


def create_transaction(transaction: Transaction):
    """
    Create a new transaction.
    
    Args:
        transaction: Transaction object
        
    """
    try:
        # Save to DynamoDB
        get_transactions_table().put_item(Item=transaction.to_dict())
        
        return transaction
    except Exception as e:
        logger.error(f"Error creating transaction: {str(e)}")
        raise


def delete_transactions_for_file(file_id: str) -> int:
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
                for transaction in transactions:
                    batch.delete_item(Key={'transactionId': transaction.transaction_id})
            
            logger.info(f"Deleted {count} transactions for file {file_id}")
        
        return count
    except ClientError as e:
        logger.error(f"Error deleting transactions for file {file_id}: {str(e)}")
        raise


def delete_file_metadata(file_id: str) -> bool:
    """
    Delete a file metadata record from the files table.
    
    Args:
        file_id: The ID of the file to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        get_files_table().delete_item(Key={'fileId': file_id})
        logger.info(f"Deleted file metadata for {file_id}")
        return True
    except ClientError as e:
        logger.error(f"Error deleting file metadata {file_id}: {str(e)}")
        raise


def get_file_map(file_map_id: Optional[str] = None) -> Optional[FileMap]:
    """
    Get a file map by ID.
    
    Args:
        file_map_id: ID of the file map to retrieve
        
    Returns:
        FileMap instance if found, None otherwise
    """
    try:
        if file_map_id:
            response = get_file_maps_table().get_item(
                Key={'fileMapId': file_map_id}
            )
        
        if 'Item' in response:
            return FileMap.from_dict(response['Item'])
        return None
    except Exception as e:
        logger.error(f"Error getting file map {file_map_id}: {str(e)}")
        return None


def get_account_default_file_map(account_id: str) -> Optional[FileMap]:
    """
    Get the default file map for an account.
    
    Args:
        account_id: ID of the account
        
    Returns:
        FileMap instance if found, None otherwise
    """
    try:
        # Get the account record
        response = get_accounts_table().get_item(
            Key={'accountId': account_id}
        )
        
        if 'Item' not in response:
            return None
            
        # Check for default field map
        default_file_map_id = response['Item'].get('defaultFileMapId')
        if not default_file_map_id:
            return None
            
        # Get the field map
        return get_file_map(default_file_map_id)
    except Exception as e:
        logger.error(f"Error getting default file map for account {account_id}: {str(e)}")
        return None


def create_file_map(file_map: FileMap) -> bool:
    """
    Create a new file map.
    
    Args:
        file_map: FileMap instance to create
        
    Returns:
        True if successful, False otherwise
    """
    try:
        get_file_maps_table().put_item(
            Item=file_map.to_dict(),
            ConditionExpression='attribute_not_exists(fileMapId)'
        )
        return True
    except Exception as e:
        logger.error(f"Error creating file map: {str(e)}")
        return False


def update_file_map(file_map: FileMap) -> bool:
    """
    Update an existing file map.
    
    Args:
        file_map: FileMap instance to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        get_file_maps_table().put_item(
            Item=file_map.to_dict(),
            ConditionExpression='attribute_exists(fileMapId)'
        )
        return True
    except Exception as e:
        logger.error(f"Error updating file map: {str(e)}")
        return False


def delete_file_map(file_map_id: str) -> bool:
    """
    Delete a file map.
    
    Args:
        file_map_id: ID of the file map to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        get_file_maps_table().delete_item(
            Key={'fileMapId': file_map_id}
        )
        return True
    except Exception as e:
        logger.error(f"Error deleting file map: {str(e)}")
        return False


def list_file_maps_by_user(user_id: str) -> List[FileMap]:
    """
    List all file maps for a user.
    
    Args:
        user_id: ID of the user
        
    Returns:
        List of FileMap instances
    """
    try:
        response = get_file_maps_table().query(
            IndexName='userId-index',
            KeyConditionExpression='userId = :userId',
            ExpressionAttributeValues={':userId': user_id}
        )
        
        return [FileMap.from_dict(item) for item in response.get('Items', [])]
    except Exception as e:
        logger.error(f"Error listing file maps for user {user_id}: {str(e)}")
        return []


def list_account_file_maps(account_id: str) -> List[FileMap]:
    """
    List all file maps for an account.
    
    Args:
        account_id: ID of the account
        
    Returns:
        List of FileMap instances
    """
    try:
        response = get_file_maps_table().query(
            IndexName='accountId-index',
            KeyConditionExpression='accountId = :accountId',
            ExpressionAttributeValues={':accountId': account_id}
        )
        
        return [FileMap.from_dict(item) for item in response.get('Items', [])]
    except Exception as e:
        logger.error(f"Error listing file maps for account {account_id}: {str(e)}")
        return []


def list_account_transactions(account_id: str, limit: int = 50, last_evaluated_key: Optional[Dict] = None) -> List[Transaction]:
    """List transactions for an account with pagination, sorted by date.
    
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
            'KeyConditionExpression': Key('accountId').eq(account_id),
            'FilterExpression': Attr('status').ne('duplicate'),
            'Limit': limit,
            'ScanIndexForward': True  # Sort in ascending order (oldest first)
        }
        
        if last_evaluated_key:
            query_params['ExclusiveStartKey'] = last_evaluated_key
            
        response = get_transactions_table().query(**query_params)
        
        # Convert items to Transaction objects
        transactions = [Transaction.from_dict(item) for item in response.get('Items', [])]
        
        # Sort by import order within each date
        transactions.sort(key=lambda x: (x.date, x.import_order or 0))
            
        return transactions
        
    except Exception as e:
        logger.error(f"Error listing transactions for account {account_id}: {str(e)}")
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
                            'status': new_status
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
        update_expression = "SET accountId = :accountId"
        expression_attribute_values = {":accountId": account_id}
        table.update_item(
            Key={'fileId': file_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
    except Exception as e:
        logger.error(f"Error updating accountId for file {file_id}: {str(e)}")
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
        update_expression = "SET fieldMapId = :fieldMapId"
        expression_attribute_values = {":fieldMapId": field_map_id}
        table.update_item(
            Key={'fileId': file_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
    except Exception as e:
        logger.error(f"Error updating fieldMapId for file {file_id}: {str(e)}")
        raise


def get_transaction_by_account_and_hash(account_id: str, transaction_hash: int) -> Optional[Transaction]:
    """
    Retrieve a transaction by accountId and transactionHash using the TransactionHashIndex.
    Args:
        account_id: The account ID
        transaction_hash: The transaction hash
    Returns:
        Transaction object if found, None otherwise
    """
    try:
        response = get_transactions_table().query(
            IndexName='TransactionHashIndex',
            KeyConditionExpression=Key('accountId').eq(account_id) & Key('transactionHash').eq(transaction_hash)
        )
        items = response.get('Items', [])
        if items:
            
            return Transaction.from_dict(items[0])
        return None
    except Exception as e:
        logger.error(f"Error retrieving transaction by account and hash: {str(e)}")
        return None


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
        get_transactions_table().put_item(Item=transaction.to_dict())
    except ClientError as e:
        logger.error(f"Error updating transaction {transaction.transaction_id}: {str(e)}")
        raise e
