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

# Initialize table resources
accounts_table = dynamodb.Table(ACCOUNTS_TABLE)
files_table = dynamodb.Table(FILES_TABLE)
transactions_table = dynamodb.Table(TRANSACTIONS_TABLE)


def get_account(account_id: str) -> Optional[Account]:
    """
    Retrieve an account by ID.
    
    Args:
        account_id: The unique identifier of the account
        
    Returns:
        Account object if found, None otherwise
    """
    try:
        response = accounts_table.get_item(Key={'accountId': account_id})
        
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
        response = accounts_table.query(
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
        accounts_table.put_item(Item=account.to_dict())
        
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
        accounts_table.put_item(Item=account.to_dict())
        
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
        
        # Update associated files to remove the account association
        for file in associated_files:
            try:
                # Create updated file data without the account association
                updated_data = file.to_dict()
                updated_data.pop('accountId', None)  # Remove the account ID association
                
                # Update the file
                update_transaction_file(file.file_id, updated_data)
                logger.info(f"Removed account association from file {file.file_id}")
            except Exception as file_error:
                logger.error(f"Error updating file {file.file_id}: {str(file_error)}")
                # Continue with other files
        
        # Delete the account
        accounts_table.delete_item(Key={'accountId': account_id})
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
        response = files_table.get_item(Key={'fileId': file_id})
        
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
        response = files_table.query(
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
        response = files_table.query(
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
        files_table.put_item(Item=file.to_dict())
        
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
        
        # Update processing status if provided
        if 'processingStatus' in update_data:
            status = update_data['processingStatus']
            record_count = int(update_data['recordCount']) if 'recordCount' in update_data else None
            
            date_range = None
            if 'dateRange' in update_data:
                dr = update_data['dateRange']
                date_range = (dr['startDate'], dr['endDate'])
                
            error_message = update_data.get('errorMessage')
            
            file.update_processing_status(
                status=status,
                record_count=record_count,
                date_range=date_range,
                error_message=error_message
            )
        
        # Save updates to DynamoDB
        files_table.put_item(Item=file.to_dict())
        
        return file
    except ValueError as e:
        logger.error(f"Validation error updating file {file_id}: {str(e)}")
        raise
    except ClientError as e:
        logger.error(f"Error updating file {file_id}: {str(e)}")
        raise


def delete_transaction_file(file_id: str) -> bool:
    """
    Delete a transaction file.
    
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
        
        # Delete the file
        files_table.delete_item(Key={'fileId': file_id})
        
        return True
    except ClientError as e:
        logger.error(f"Error deleting file {file_id}: {str(e)}")
        raise


def list_file_transactions(file_id: str) -> List[Dict[str, Any]]:
    """
    List all transactions for a specific file.
    
    Args:
        file_id: ID of the file to get transactions for
        
    Returns:
        List of transaction objects
    """
    try:
        response = transactions_table.query(
            IndexName='FileIdIndex',
            KeyConditionExpression=Key('fileId').eq(file_id)
        )
        return response.get('Items', [])
    except Exception as e:
        logger.error(f"Error listing transactions for file {file_id}: {str(e)}")
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
        transactions_table.put_item(Item=transaction.to_dict())
        
        return transaction
    except Exception as e:
        logger.error(f"Error creating transaction: {str(e)}")
        raise


def delete_file_transactions(file_id: str) -> int:
    """
    Delete all transactions for a file.
    
    Args:
        file_id: ID of the file whose transactions should be deleted
        
    Returns:
        Number of deleted transactions
    """
    try:
        # First, get all transactions for the file
        transactions = list_file_transactions(file_id)
        deleted_count = 0
        
        # Delete each transaction
        with transactions_table.batch_writer() as batch:
            for transaction in transactions:
                batch.delete_item(
                    Key={
                        'transactionId': transaction['transactionId']
                    }
                )
                deleted_count += 1
        
        logger.info(f"Deleted {deleted_count} transactions for file {file_id}")
        return deleted_count
    except Exception as e:
        logger.error(f"Error deleting transactions for file {file_id}: {str(e)}")
        raise 