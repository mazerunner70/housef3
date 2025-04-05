"""
Utility functions for database operations.
"""
import os
import logging
import boto3
from typing import Dict, List, Any, Optional, Union
from botocore.exceptions import ClientError

from ..models import (
    Account, 
    TransactionFile,
    validate_account_data,
    validate_transaction_file_data
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')

# Get environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
ACCOUNTS_TABLE = os.environ.get('ACCOUNTS_TABLE')
FILES_TABLE = os.environ.get('FILES_TABLE')

# Initialize table resources
accounts_table = dynamodb.Table(ACCOUNTS_TABLE)
files_table = dynamodb.Table(FILES_TABLE)


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
        
        # Create account object
        account = Account.create(
            user_id=account_data['userId'],
            account_name=account_data['accountName'],
            account_type=account_data['accountType'],
            institution=account_data['institution'],
            balance=float(account_data.get('balance', 0)),
            currency=account_data.get('currency', 'USD'),
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
    Delete an account.
    
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
        
        # Delete the account
        accounts_table.delete_item(Key={'accountId': account_id})
        
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
        
        # Create transaction file object
        file = TransactionFile.create(
            account_id=file_data['accountId'],
            user_id=file_data['userId'],
            file_name=file_data['fileName'],
            file_size=int(file_data['fileSize']),
            file_format=file_data['fileFormat'],
            s3_key=file_data['s3Key'],
            processing_status=file_data.get('processingStatus', 'pending')
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