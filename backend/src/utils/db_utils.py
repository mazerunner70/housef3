"""
Utility functions for database operations.
"""
import os
import logging
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
    Currency,
    FileFormat,
    ProcessingStatus
)
from models.transaction import Transaction
from boto3.dynamodb.conditions import Key
from models.field_map import FieldMap

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
FIELD_MAPS_TABLE = os.environ.get('FIELD_MAPS_TABLE')

# Initialize table resources lazily
_accounts_table = None
_files_table = None
_transactions_table = None
_field_maps_table = None

def get_accounts_table():
    """Get the accounts table resource, initializing it if needed."""
    global _accounts_table
    if _accounts_table is None and ACCOUNTS_TABLE:
        _accounts_table = dynamodb.Table(ACCOUNTS_TABLE)
    return _accounts_table

def get_files_table():
    """Get the files table resource, initializing it if needed."""
    global _files_table
    if _files_table is None and FILES_TABLE:
        _files_table = dynamodb.Table(FILES_TABLE)
    return _files_table

def get_transactions_table():
    """Get the transactions table resource, initializing it if needed."""
    global _transactions_table
    if _transactions_table is None and TRANSACTIONS_TABLE:
        _transactions_table = dynamodb.Table(TRANSACTIONS_TABLE)
    return _transactions_table

def get_field_maps_table():
    """Get the field maps table resource, initializing it if needed."""
    global _field_maps_table
    if _field_maps_table is None and FIELD_MAPS_TABLE:
        _field_maps_table = dynamodb.Table(FIELD_MAPS_TABLE)
    return _field_maps_table

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
            KeyConditionExpression=boto3.dynamodb.conditions.Key('userId').eq(user_id)
        )
        
        accounts = []
        for item in response.get('Items', []):
            accounts.append(Account.from_dict(item))
            
        return accounts
    except ClientError as e:
        logger.error(f"Error listing accounts for user {user_id}: {str(e)}")
        raise


def create_account(account_data: Dict[str, Any]) -> Account:
    """
    Create a new account.
    
    Args:
        account_data: Dictionary containing account data
        
    Returns:
        Newly created Account object
    """
    try:
        # Validate the input data
        validate_account_data(account_data)
        
        # Ensure account_type and currency are proper enum types
        account_type = account_data['accountType']
        if isinstance(account_type, str):
            account_type = AccountType(account_type)
            
        currency = account_data.get('currency', 'USD')
        if isinstance(currency, str):
            currency = Currency(currency)
        
        # Create account object
        account = Account.create(
            user_id=account_data['userId'],
            account_name=account_data['accountName'],
            account_type=account_type,
            institution=account_data['institution'],
            balance=float(account_data.get('balance', 0)),
            currency=currency,
            notes=account_data.get('notes'),
            is_active=account_data.get('isActive', True)
        )
        
        # Save to DynamoDB
        get_accounts_table().put_item(Item=account.to_dict())
        
        return account
    except ValueError as e:
        logger.error(f"Validation error creating account: {str(e)}")
        raise
    except ClientError as e:
        logger.error(f"Error creating account: {str(e)}")
        raise


def update_account(account_id: str, update_data: Dict[str, Any]) -> Account:
    """
    Update an existing account.
    
    Args:
        account_id: The unique identifier of the account to update
        update_data: Dictionary containing fields to update
        
    Returns:
        Updated Account object
    """
    try:
        # Retrieve the existing account
        account = get_account(account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")
        
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
            'isActive': 'is_active'
        }
        
        for key, value in update_data.items():
            if key in field_mapping:
                update_data_snake_case[field_mapping[key]] = value
        
        account.update(**update_data_snake_case)
        
        # Save updates to DynamoDB
        get_accounts_table().put_item(Item=account.to_dict())
        
        return account
    except ValueError as e:
        logger.error(f"Validation error updating account {account_id}: {str(e)}")
        raise
    except ClientError as e:
        logger.error(f"Error updating account {account_id}: {str(e)}")
        raise


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
            KeyConditionExpression=boto3.dynamodb.conditions.Key('accountId').eq(account_id)
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
            KeyConditionExpression=boto3.dynamodb.conditions.Key('userId').eq(user_id)
        )
        
        files = []
        for item in response.get('Items', []):
            files.append(TransactionFile.from_dict(item))
            
        return files
    except ClientError as e:
        logger.error(f"Error listing files for user {user_id}: {str(e)}")
        raise


def create_transaction_file(file_data: Dict[str, Any]) -> TransactionFile:
    """
    Create a new transaction file record.
    
    Args:
        file_data: Dictionary containing file data
        
    Returns:
        Newly created TransactionFile object
    """
    try:
        # Validate the input data
        validate_transaction_file_data(file_data)
        
        # Convert string values to enum types if provided as strings
        if 'fileFormat' in file_data and isinstance(file_data['fileFormat'], str):
            file_data['fileFormat'] = FileFormat(file_data['fileFormat'])
            
        if 'processingStatus' in file_data and isinstance(file_data['processingStatus'], str):
            file_data['processingStatus'] = ProcessingStatus(file_data['processingStatus'])
        
        # Check if file_id is provided or should be generated
        file_id = file_data.get('fileId', str(uuid.uuid4()))
        
        # Create transaction file object
        file = TransactionFile(
            file_id=file_id,
            account_id=file_data['accountId'],
            user_id=file_data['userId'],
            file_name=file_data['fileName'],
            upload_date=datetime.utcnow().isoformat(),
            file_size=int(file_data['fileSize']),
            file_format=file_data['fileFormat'],
            s3_key=file_data['s3Key'],
            processing_status=file_data.get('processingStatus', ProcessingStatus.PENDING)
        )
        
        # Save to DynamoDB
        get_files_table().put_item(Item=file.to_dict())
        
        return file
    except ValueError as e:
        logger.error(f"Validation error creating file: {str(e)}")
        raise
    except ClientError as e:
        logger.error(f"Error creating file: {str(e)}")
        raise


def update_transaction_file(file_id: str, update_data: Dict[str, Any]) -> TransactionFile:
    """
    Update an existing transaction file.
    
    Args:
        file_id: The unique identifier of the file to update
        update_data: Dictionary containing fields to update
        
    Returns:
        Updated TransactionFile object
    """
    try:
        # Retrieve the existing file
        file = get_transaction_file(file_id)
        if not file:
            raise ValueError(f"File {file_id} not found")
        
        # Get the current file data as a dictionary
        file_dict = file.to_dict()
        
        # Update with new data
        for key, value in update_data.items():
            if value is None:
                # If value is None, remove the field
                file_dict.pop(key, None)
            else:
                file_dict[key] = value
        
        # Create a new TransactionFile object with updated data
        updated_file = TransactionFile.from_dict(file_dict)
        
        # Save updates to DynamoDB
        get_files_table().put_item(Item=file_dict)
        
        return updated_file
    except ValueError as e:
        logger.error(f"Validation error updating file {file_id}: {str(e)}")
        raise
    except ClientError as e:
        logger.error(f"Error updating file {file_id}: {str(e)}")
        raise


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


def list_file_transactions(file_id: str) -> List[Dict[str, Any]]:
    """
    List all transactions for a specific file.
    
    Args:
        file_id: The unique identifier of the file
        
    Returns:
        List of transaction dictionaries
    """
    try:
        response = get_transactions_table().query(
            IndexName='FileIdIndex',
            KeyConditionExpression=Key('fileId').eq(file_id)
        )
        return response.get('Items', [])
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


def create_transaction(transaction_data: Dict[str, Any]) -> Transaction:
    """
    Create a new transaction.
    
    Args:
        transaction_data: Dictionary containing transaction data
        
    Returns:
        The created Transaction object
    """
    try:
        # Create a Transaction object
        transaction = Transaction.create(**transaction_data)
        
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
                    batch.delete_item(Key={'transactionId': transaction['transactionId']})
            
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


def get_field_map(field_map_id: str) -> Optional[FieldMap]:
    """
    Get a field map by ID.
    
    Args:
        field_map_id: ID of the field map to retrieve
        
    Returns:
        FieldMap instance if found, None otherwise
    """
    try:
        response = get_field_maps_table().get_item(
            Key={'fieldMapId': field_map_id}
        )
        
        if 'Item' in response:
            return FieldMap.from_dict(response['Item'])
        return None
    except Exception as e:
        logger.error(f"Error getting field map {field_map_id}: {str(e)}")
        return None


def get_account_default_field_map(account_id: str) -> Optional[FieldMap]:
    """
    Get the default field map for an account.
    
    Args:
        account_id: ID of the account
        
    Returns:
        FieldMap instance if found, None otherwise
    """
    try:
        # Get the account record
        response = get_accounts_table().get_item(
            Key={'accountId': account_id}
        )
        
        if 'Item' not in response:
            return None
            
        # Check for default field map
        default_field_map_id = response['Item'].get('defaultFieldMapId')
        if not default_field_map_id:
            return None
            
        # Get the field map
        return get_field_map(default_field_map_id)
    except Exception as e:
        logger.error(f"Error getting default field map for account {account_id}: {str(e)}")
        return None


def create_field_map(field_map: FieldMap) -> bool:
    """
    Create a new field map.
    
    Args:
        field_map: FieldMap instance to create
        
    Returns:
        True if successful, False otherwise
    """
    try:
        get_field_maps_table().put_item(
            Item=field_map.to_dict(),
            ConditionExpression='attribute_not_exists(fieldMapId)'
        )
        return True
    except Exception as e:
        logger.error(f"Error creating field map: {str(e)}")
        return False


def update_field_map(field_map: FieldMap) -> bool:
    """
    Update an existing field map.
    
    Args:
        field_map: FieldMap instance to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        get_field_maps_table().put_item(
            Item=field_map.to_dict(),
            ConditionExpression='attribute_exists(fieldMapId)'
        )
        return True
    except Exception as e:
        logger.error(f"Error updating field map: {str(e)}")
        return False


def delete_field_map(field_map_id: str) -> bool:
    """
    Delete a field map.
    
    Args:
        field_map_id: ID of the field map to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        get_field_maps_table().delete_item(
            Key={'fieldMapId': field_map_id}
        )
        return True
    except Exception as e:
        logger.error(f"Error deleting field map: {str(e)}")
        return False


def list_field_maps_by_user(user_id: str) -> List[FieldMap]:
    """
    List all field maps for a user.
    
    Args:
        user_id: ID of the user
        
    Returns:
        List of FieldMap instances
    """
    try:
        response = get_field_maps_table().query(
            IndexName='userId-index',
            KeyConditionExpression='userId = :userId',
            ExpressionAttributeValues={':userId': user_id}
        )
        
        return [FieldMap.from_dict(item) for item in response.get('Items', [])]
    except Exception as e:
        logger.error(f"Error listing field maps for user {user_id}: {str(e)}")
        return []


def list_account_field_maps(account_id: str) -> List[FieldMap]:
    """
    List all field maps for an account.
    
    Args:
        account_id: ID of the account
        
    Returns:
        List of FieldMap instances
    """
    try:
        response = get_field_maps_table().query(
            IndexName='accountId-index',
            KeyConditionExpression='accountId = :accountId',
            ExpressionAttributeValues={':accountId': account_id}
        )
        
        return [FieldMap.from_dict(item) for item in response.get('Items', [])]
    except Exception as e:
        logger.error(f"Error listing field maps for account {account_id}: {str(e)}")
        return [] 