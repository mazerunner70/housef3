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
from utils.transaction_parser import parse_transactions, file_type_selector
from models.transaction import Transaction
from utils.file_analyzer import analyze_file_format
from utils.db_utils import (
    create_transaction_file,
    get_account,
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
import time

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

def process_file_with_account(file_id: str, content_bytes: bytes, opening_balance: Decimal, user_id: str) -> Dict[str, Any]:
    """
    Process a file and its transactions with account-specific logic.
    This includes:
    - Field map handling (account-specific or file-specific)
    - Duplicate transaction detection
    - Account association
    - Transaction status tracking
    - Opening balance calculation from duplicates
    - File format determination
    
    Args:
        file_id: ID of the file to process
        content_bytes: File content as bytes
        opening_balance: Opening balance to use for running totals (as Decimal)
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

        # Determine file format if not already set
        file_format = None
        if hasattr(file_record, 'file_format') and file_record.file_format:
            try:
                file_format = FileFormat(file_record.file_format)
            except ValueError:
                logger.warning(f"Invalid file format stored: {file_record.file_format}, will re-detect")
                
        if not file_format:
            file_format = file_type_selector(content_bytes)
            logger.info(f"Detected file format: {file_format}")
            # Update file record with detected format
            update_transaction_file(file_id, {"file_format": file_format.value})
            
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

def handler(event, context):
    """
    Lambda handler for processing transaction files via S3 upload events only.
    Handles only S3 event triggers.
    """
    try:
        logger.info(f"Lambda invoked with event: {json.dumps(event)[:1000]}")
        # S3 event trigger path only
        if "Records" in event and "s3" in event["Records"][0]:
            record = event["Records"][0]
            bucket = record["s3"]["bucket"]["name"]
            key = record["s3"]["object"]["key"]
            size = record["s3"]["object"].get("size", 0)
            logger.info(f"Processing S3 event for bucket: {bucket}, key: {key}")

            # Extract user_id and file_id from the key path (format: user_id/file_id/filename)
            key_parts = key.split('/')
            if len(key_parts) != 3:
                logger.error(f"Invalid S3 key format: {key}")
                return {
                    'statusCode': 400,
                    'body': json.dumps({'message': 'Invalid S3 key format'})
                }
            
            user_id = key_parts[0]
            file_id = key_parts[1]
            file_name = key_parts[2]

            try:
                # Get object metadata first to check for account ID
                object_metadata = s3_client.head_object(Bucket=bucket, Key=key)
                logger.info(f"S3 object metadata: {json.dumps(object_metadata.get('Metadata', {}))}")
                account_id = object_metadata.get('Metadata', {}).get('accountid')
                logger.info(f"Found account ID in metadata: {account_id}")

                # Download file from S3
                logger.info(f"Attempting to download file from S3: {bucket}/{key}")
                content_bytes = s3_client.get_object(Bucket=bucket, Key=key)["Body"].read()
                logger.info(f"Successfully downloaded file from S3, size: {len(content_bytes)} bytes")

                # Detect file type
                file_format = file_type_selector(content_bytes)
                logger.info(f"Detected file format: {file_format}")

                # Create or update file metadata in DynamoDB
                current_time = datetime.utcnow().isoformat()
                file_data = {
                    'fileId': file_id,
                    'userId': user_id,
                    'fileName': file_name,
                    'fileSize': size,
                    'uploadDate': current_time,
                    'lastModified': current_time,
                    's3Key': key,
                    'fileFormat': file_format.value,
                    'processingStatus': ProcessingStatus.PENDING.value
                }

                # Add account ID if it was found in metadata
                if account_id:
                    file_data['accountId'] = account_id
                    logger.info(f"Adding account ID to file metadata: {account_id}")
                # If account has a default field map, add it to the file metadata
                if account_id:
                    account = get_account(account_id)
                    if account and account.default_field_map_id:
                        file_data['fieldMapId'] = account.default_field_map_id
                        logger.info(f"Adding default field map ID to file metadata: {account.default_field_map_id}")

                # Create the file record
                create_transaction_file(file_data)
                logger.info(f"Created file metadata in DynamoDB: {json.dumps(file_data)}")

                process_file_with_account(file_id, content_bytes, Decimal('0'), user_id)
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'message': 'File processed and metadata created.',
                        'fileId': file_id,
                        'fileFormat': file_format.value
                    })
                }

            except s3_client.exceptions.NoSuchKey:
                logger.error(f"File not found in S3: {bucket}/{key}")
                return {
                    'statusCode': 404,
                    'body': json.dumps({'message': 'File not found in S3 bucket'})
                }
            except Exception as s3_error:
                logger.error(f"Error processing file: {str(s3_error)}")
                return {
                    'statusCode': 500,
                    'body': json.dumps({'message': f'Error processing file: {str(s3_error)}'})
                }
        else:
            logger.error("Lambda invoked with unsupported event structure (not an S3 event)")
            return {
                'statusCode': 400,
                'body': json.dumps({'message': 'Unsupported event structure: expected S3 event'})
            }
    except Exception as e:
        logger.error(f"Error in file processor lambda: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': f'Error processing file: {str(e)}'
            })
        }

def update_transaction_file(file_id: str, updates: Dict[str, Any]) -> None:
    """Update a transaction file record in DynamoDB."""
    try:
        # Convert snake_case keys to camelCase for DynamoDB
        update_expr_parts = []
        expr_attr_names = {}
        expr_attr_values = {}
        
        key_mapping = {
            'processing_status': 'processingStatus',
            'record_count': 'recordCount',
            'date_range_start': 'dateRangeStart',
            'date_range_end': 'dateRangeEnd',
            'error_message': 'errorMessage',
            'opening_balance': 'openingBalance',
            'account_id': 'accountId'
        }
        
        for key, value in updates.items():
            # Convert snake_case to camelCase if needed
            dynamo_key = key_mapping.get(key, key)
            
            # Build update expression
            attr_name = f"#{key.replace('_', '')}"
            attr_value = f":{key.replace('_', '')}"
            update_expr_parts.append(f"{attr_name} = {attr_value}")
            expr_attr_names[attr_name] = dynamo_key
            expr_attr_values[attr_value] = value
            
        update_expression = "SET " + ", ".join(update_expr_parts)
        
        # Use the correct file_table instead of transaction_table
        file_table.update_item(
            Key={'fileId': file_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values
        )
        logger.info(f"Updated transaction file {file_id} with {updates}")
    except Exception as e:
        logger.error(f"Error updating transaction file {file_id}: {str(e)}")
        raise 