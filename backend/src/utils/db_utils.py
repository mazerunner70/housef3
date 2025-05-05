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
from boto3.dynamodb.conditions import Key, Attr
from models.field_map import FieldMap
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
            'isActive': 'is_active',
            'defaultFieldMapId': 'default_field_map_id'
        }
        
        for key, value in update_data.items():
            if key in field_mapping:
                update_data_snake_case[field_mapping[key]] = value
            else:
                raise ValueError(f"Skipping update for field {key}")
        
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
        file = TransactionFile.from_dict({
            'fileId': file_id,
            'accountId': file_data.get('accountId'),
            'userId': file_data['userId'],
            'fileName': file_data['fileName'],
            'uploadDate': datetime.utcnow().isoformat(),
            'fileSize': int(file_data['fileSize']),
            'fileFormat': file_data.get('fileFormat'),
            's3Key': file_data['s3Key'],
            'processingStatus': file_data.get('processingStatus', ProcessingStatus.PENDING)
        })
        
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


def create_transaction(transaction_data: Dict[str, Any]) -> Transaction:
    """
    Create a new transaction.
    
    Args:
        transaction_data: Dictionary containing transaction data
        
    Returns:
        The created Transaction object
    """
    try:
        # Check for duplicates first
        is_duplicate = check_duplicate_transaction(transaction_data, transaction_data['account_id'])
        if is_duplicate:
            logger.info(f"Duplicate transaction found, skipping creation")
            transaction_data['status'] = 'duplicate'
        else:
            transaction_data['status'] = 'new'

        # Generate transaction hash
        transaction_hash = generate_transaction_hash(
            transaction_data['account_id'],
            transaction_data['date'],
            Decimal(str(transaction_data['amount'])),
            transaction_data['description']
        )
        
        # Add hash to transaction data
        transaction_data['transaction_hash'] = transaction_hash
        
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
    
def check_duplicate_transaction(transaction: Dict[str, Any], account_id: str) -> bool:
    """
    Check if a transaction already exists for the given account using numeric hash.
    
    Args:
        transaction: Dictionary containing transaction details
        account_id: ID of the account to check for duplicates
        
    Returns:
        bool: True if duplicate found, False otherwise
    """
    try:
        logger.info(f"Entering check_duplicate_transaction for account_id: {account_id}")
        transaction_hash = generate_transaction_hash(
            account_id,
            transaction['date'],
            Decimal(str(transaction['amount'])),
            transaction['description']
        )
        existing = get_transaction_by_account_and_hash(account_id, transaction_hash)
        return existing is not None
    except Exception as e:
        logger.error(f"Error checking for duplicate transaction: {str(e)}")
        return False 
