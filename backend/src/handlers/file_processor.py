"""
Lambda handler for processing uploaded files in S3 and analyzing their format.
This function is triggered by S3 ObjectCreated events.
"""
import json
import logging
import os
import urllib.parse
import re
import boto3
from typing import Dict, Any, List, Tuple, Optional
from decimal import Decimal
from models.transaction_file import FileFormat, ProcessingStatus
from models.field_map import FieldMap
from utils.transaction_parser import parse_transactions
from models.transaction import Transaction
from utils.file_analyzer import analyze_file_format
from utils.db_utils import (
    get_transaction_file,
    update_transaction_file,
    create_transaction,
    delete_transactions_for_file,
    get_field_map,
    get_account_default_field_map
)
from utils.file_processor_utils import (
    check_duplicate_transaction,
    extract_opening_balance,
    extract_opening_balance_ofx,
    extract_opening_balance_csv,
    find_file_records_by_s3_key,
    get_file_content,
    calculate_opening_balance_from_duplicates
)
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Fix imports for Lambda environment
try:
    import sys
    # Add the Lambda root to the path if not already there
    if '/var/task' not in sys.path:
        sys.path.insert(0, '/var/task')
    
    # Add the parent directory to allow imports
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # Import required modules
    from models.transaction_file import FileFormat, ProcessingStatus
    from utils.file_analyzer import analyze_file_format
    from utils.db_utils import get_transaction_file, update_transaction_file
    
    logger.info("Successfully imported modules for file processor")
except ImportError as e:
    logger.error(f"Import error in file processor: {str(e)}")
    logger.error(f"Current sys.path: {sys.path}")
    try:
        from ..models.transaction_file import FileFormat, ProcessingStatus
        from ..utils.file_analyzer import analyze_file_format
        from ..utils.db_utils import get_transaction_file, update_transaction_file
        logger.info("Successfully imported modules using relative imports")
    except ImportError as e2:
        logger.error(f"Final import attempt failed in file processor: {str(e2)}")
        raise

# Initialize clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
FILES_TABLE = os.environ.get('FILES_TABLE', 'transaction-files')
file_table = dynamodb.Table(FILES_TABLE)

# Get table names from environment variables
FILE_TABLE_NAME = os.environ.get('FILES_TABLE', 'transaction-files')
TRANSACTIONS_TABLE = os.environ.get('TRANSACTIONS_TABLE', 'transactions')
FIELD_MAPS_TABLE = os.environ.get('FIELD_MAPS_TABLE', 'field-maps')

# Initialize DynamoDB tables
transaction_table = dynamodb.Table(TRANSACTIONS_TABLE)
field_maps_table = dynamodb.Table(FIELD_MAPS_TABLE)

def process_file_with_account(file_id: str, content_bytes: bytes, file_format: FileFormat, opening_balance: float, user_id: str) -> Dict[str, Any]:
    """
    Process a file and its transactions with account-specific logic.
    This includes:
    - Field map handling (account-specific or file-specific)
    - Duplicate transaction detection
    - Account association
    - Transaction status tracking
    - Opening balance calculation from duplicates
    
    Args:
        file_id: ID of the file to process
        content_bytes: File content as bytes
        file_format: Format of the file
        opening_balance: Opening balance to use for running totals
        user_id: ID of the user who owns the file
        
    Returns:
        Dict[str, Any]: Response containing success status and message
    """
    try:
        # Get the file record to check for field map
        file_record = get_transaction_file(file_id)
        if not file_record:
            return {
                'statusCode': 404,
                'body': json.dumps({'message': 'File not found'})
            }
            
        # Get field map if specified
        field_map = None
        field_map_id = file_record.field_map_id
        account_id = file_record.account_id
        logger.info(f"Field map ID: {field_map_id}")
        logger.info(f"Account ID: {account_id}")
        if field_map_id:
            # Use specified field map
            field_map = get_field_map(field_map_id)
            if not field_map:
                return {
                    'statusCode': 404,
                    'body': json.dumps({'message': 'Field map not found'})
                }
        elif account_id:
            # Try to use account's default field map
            field_map = get_account_default_field_map(account_id)
            if field_map:
                logger.info(f"Using account default field map for file {file_id}")
                
        if not field_map and file_format == FileFormat.CSV:
            return {
                'statusCode': 400,
                'body': json.dumps({'message': 'Field map required for CSV files'})
            }
            
        # Parse transactions using the utility
        try:
            transactions = parse_transactions(
                content_bytes, 
                file_format,
                opening_balance,
                field_map
            )
        except Exception as parse_error:
            logger.error(f"Error parsing transactions: {str(parse_error)}")
            return {
                'statusCode': 400,
                'body': json.dumps({'message': f'Error parsing transactions: {str(parse_error)}'})
            }
        
        if not transactions:
            return {
                'statusCode': 400,
                'body': json.dumps({'message': 'No transactions could be parsed from file'})
            }
            
        # Calculate opening balance from duplicates if possible
        if account_id:
            calculated_opening_balance = calculate_opening_balance_from_duplicates(transactions, account_id)
            if calculated_opening_balance is not None:
                opening_balance = calculated_opening_balance  # Already a Decimal from calculate_opening_balance_from_duplicates
                logger.info(f"Calculated opening balance from duplicates: {opening_balance}")
                update_transaction_file(file_id, {'openingBalance': str(opening_balance)})
                
                # Recalculate running balances with new opening balance
                current_balance = opening_balance
                for tx in transactions:
                    current_balance += Decimal(str(tx['amount']))
                    tx['balance'] = str(current_balance)
                logger.info("Recalculated running balances with new opening balance")
            
        # Delete existing transactions if any
        delete_transactions_for_file(file_id)
        
        # Save transactions to the database
        transaction_count = 0
        duplicate_count = 0
        for transaction_data in transactions:
            try:
                # Add the file_id and user_id to each transaction
                transaction_data['file_id'] = file_id
                transaction_data['user_id'] = user_id
                if account_id:
                    transaction_data['account_id'] = account_id
                
                # Check for duplicates if we have an account_id
                is_duplicate = False
                if account_id:
                    is_duplicate = check_duplicate_transaction(transaction_data, account_id)
                    if is_duplicate:
                        transaction_data['status'] = 'duplicate'
                        duplicate_count += 1
                    else:
                        transaction_data['status'] = 'new'
                logger.info(f"Transaction data: {transaction_data}")
                # Create and save the transaction
                create_transaction(transaction_data)
                transaction_count += 1
            except Exception as tx_error:
                logger.error(f"Error creating transaction: {str(tx_error)}")
                logger.error(f"Error type: {type(tx_error).__name__}")
                logger.error(f"Error args: {tx_error.args}")
                logger.error(f"Transaction data that caused error: {transaction_data}")
                
        logger.info(f"Saved {transaction_count} transactions for file {file_id} ({duplicate_count} duplicates)")
        
        # Update the file record with transaction count and status
        update_data = {
            'processing_status': ProcessingStatus.PROCESSED.value,
            'processed_at': datetime.now().isoformat(),
            'transaction_count': len(transactions)
        }
        if field_map:
            update_data['fieldMapId'] = field_map.field_map_id
            
        update_transaction_file(file_id, update_data)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully processed {transaction_count} transactions',
                'transactionCount': transaction_count
            })
        }
    except Exception as e:
        logger.error(f"Error processing transactions: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error args: {e.args}")
        update_transaction_file(file_id, {
            'processingStatus': ProcessingStatus.ERROR,
            'errorMessage': f'Error processing transactions: {str(e)}'
        })
        return {
            'statusCode': 500,
            'body': json.dumps({'message': f'Error processing transactions: {str(e)}'})
        }

def lambda_handler(event, context):
    """
    Lambda handler for processing transaction files.
    """
    try:
        # Extract file ID from the event
        file_id = event.get('fileId')
        if not file_id:
            raise ValueError("No fileId provided in event")
            
        # Get the file record
        file_record = get_transaction_file(file_id)
        if not file_record:
            raise ValueError(f"File record not found for ID: {file_id}")
            
        # Get user ID and account ID
        user_id = file_record.get('userId')
        account_id = file_record.get('accountId')
        if not user_id:
            raise ValueError(f"No userId found for file: {file_id}")
            
        # Get file content from S3
        content_bytes = get_file_content(file_id)
        if not content_bytes:
            raise ValueError(f"Could not retrieve file content for ID: {file_id}")
            
        # Process the file
        response = process_file_with_account(
            file_id=file_id,
            content_bytes=content_bytes,
            file_format=file_record['file_format'],
            opening_balance=float(file_record['opening_balance']) if file_record['opening_balance'] else 0,
            user_id=user_id
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in file processor lambda: {str(e)}")
        if file_id:
            update_transaction_file(file_id, {
                'processingStatus': ProcessingStatus.ERROR,
                'errorMessage': str(e)
            })
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': f'Error processing file: {str(e)}'
            })
        } 