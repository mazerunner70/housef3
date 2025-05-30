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
from models.transaction_file import FileFormat, ProcessingStatus, TransactionFile
from models.file_map import FileMap
from services.file_processor_service import create_file, process_file
from utils.transaction_parser import parse_transactions, file_type_selector
from models.transaction import Transaction
from utils.file_analyzer import analyze_file_format
from utils.db_utils import (
    create_transaction_file,
    get_account,
    get_account_default_file_map,
    get_file_map,
    get_transaction_file,
    create_transaction,
    delete_transactions_for_file,

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
from utils.s3_dao import get_object_content, get_object_metadata
import traceback

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
    from utils.db_utils import get_transaction_file
    
    logger.info("Successfully imported modules for file processor")
except ImportError as e:
    logger.error(f"Import error in file processor: {str(e)}")
    logger.error(f"Current sys.path: {sys.path}")
    try:
        from ..models.transaction_file import FileFormat, ProcessingStatus
        from ..utils.file_analyzer import analyze_file_format
        from ..utils.db_utils import get_transaction_file
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



def handler(event, context):
    """
    Process a file that was uploaded to S3.
    
    This handler is triggered by S3 events when a file is uploaded.
    It performs the following steps:
    1. Downloads the file from S3
    2. Detects the file format
    3. Creates or updates file metadata in DynamoDB
    4. Optionally associates the file with an account if specified
    
    Args:
        event: S3 event notification
        context: Lambda context
        
    Returns:
        Dict containing processing results
    """
    try:
        # Extract file information from the S3 event
        logger.info(f"Processing S3 event: {json.dumps(event)}")
        
        # Get the S3 bucket and key from the event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        size = event['Records'][0]['s3']['object']['size']
        
        # Extract user ID and file ID from the key (format: userId/fileId/filename)
        key_parts = key.split('/')
        if len(key_parts) != 3:
            raise ValueError(f"Invalid S3 key format: {key}")
            
        user_id = key_parts[0]
        file_id = key_parts[1]
        file_name = key_parts[2]
        
        logger.info(f"Processing file upload - User: {user_id}, File: {file_id}, Name: {file_name}")

        try:
            # Get object metadata first to check for account ID
            metadata = get_object_metadata(key, bucket)
            if metadata is None:
                raise ValueError(f"Could not get metadata for file: {key}")
                
            account_id = metadata.get('metadata', {}).get('accountid')
            logger.info(f"Found account ID in metadata: {account_id}")

            # Download file from S3
            logger.info(f"Attempting to download file from S3: {bucket}/{key}")
            content_bytes = get_object_content(key, bucket)
            if content_bytes is None:
                raise ValueError(f"Could not download file content: {key}")
                
            logger.info(f"Successfully downloaded file from S3, size: {len(content_bytes)} bytes")

            # Detect file type
            file_format = file_type_selector(content_bytes)
            logger.info(f"Detected file format: {file_format}")

            # Create or update file metadata in DynamoDB
            current_time = int(datetime.utcnow().timestamp())
            transaction_file = TransactionFile(
                file_id=file_id,
                user_id=user_id,
                file_name=file_name,
                file_size=size,
                upload_date=int(current_time),
                s3_key=key,
                file_format=file_format,
                processing_status=ProcessingStatus.PENDING
            )

            # Add account ID if it was found in metadata
            if account_id:
                transaction_file.account_id = account_id
                logger.info(f"Adding account ID to file metadata: {account_id}")

            # Process the file
            response = process_file(transaction_file)
            logger.info(f"File processing complete: {json.dumps(response.to_dict())}")
            
            return {
                'statusCode': 200,
                'body': json.dumps(response.to_dict())
            }
            
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': f"Error processing file: {str(e)}"
                })
            }
            
    except Exception as e:
        logger.error(f"Error handling S3 event: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f"Error handling S3 event: {str(e)}"
            })
        }

def update_transaction_file(file_id: str, user_id: str, updates: Dict[str, Any]) -> None:
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