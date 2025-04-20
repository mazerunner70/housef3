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

def check_duplicate_transaction(transaction: Dict[str, Any], account_id: str) -> bool:
    """
    Check if a transaction is a duplicate of an existing transaction in the account.
    
    Args:
        transaction: The transaction to check
        account_id: The account ID to check against
        
    Returns:
        True if the transaction is a duplicate, False otherwise
    """
    try:
        # Query transactions table for potential duplicates
        response = transaction_table.query(
            IndexName='AccountIdIndex',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('accountId').eq(account_id),
            FilterExpression=boto3.dynamodb.conditions.Attr('date').eq(transaction['date']) &
                           boto3.dynamodb.conditions.Attr('description').eq(transaction['description']) &
                           boto3.dynamodb.conditions.Attr('amount').eq(str(transaction['amount']))
        )
        
        # If we found any matches, it's a duplicate
        return len(response.get('Items', [])) > 0
    except Exception as e:
        logger.error(f"Error checking for duplicate transaction: {str(e)}")
        return False

def process_file_with_account(file_id: str, content_bytes: bytes, file_format: FileFormat, opening_balance: float, user_id: str) -> int:
    """
    Process a file and its transactions with account-specific logic.
    This includes:
    - Field map handling (account-specific or file-specific)
    - Duplicate transaction detection
    - Account association
    - Transaction status tracking
    
    Args:
        file_id: ID of the file to process
        content_bytes: File content as bytes
        file_format: Format of the file
        opening_balance: Opening balance to use for running totals
        user_id: ID of the user who owns the file
        
    Returns:
        Number of transactions processed
    """
    try:
        # Get the file record to check for field map
        file_record = get_transaction_file(file_id)
        if not file_record:
            logger.error(f"File record not found for ID: {file_id}")
            return 0
            
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
                logger.error(f"Specified field map not found: {field_map_id}")
                update_transaction_file(file_id, {
                    'processingStatus': ProcessingStatus.ERROR,
                    'errorMessage': 'Specified field map not found'
                })
                return 0
        elif account_id:
            # Try to use account's default field map
            field_map = get_account_default_field_map(account_id)
            if field_map:
                logger.info(f"Using account default field map for file {file_id}")
                
        if not field_map and file_format == FileFormat.CSV:
            logger.warning(f"No field map found for CSV file {file_id}")
            update_transaction_file(file_id, {
                'processingStatus': ProcessingStatus.ERROR,
                'errorMessage': 'Field map required for CSV files'
            })
            return 0
            
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
            logger.error(f"Error type: {type(parse_error).__name__}")
            logger.error(f"Error args: {parse_error.args}")
            update_transaction_file(file_id, {
                'processingStatus': ProcessingStatus.ERROR,
                'errorMessage': f'Error parsing transactions: {str(parse_error)}'
            })
            return 0
        
        if not transactions:
            logger.error(f"No transactions parsed from file {file_id}")
            update_transaction_file(file_id, {
                'processingStatus': ProcessingStatus.ERROR,
                'errorMessage': 'No transactions could be parsed from file'
            })
            return 0
        
        # Delete existing transactions if any
        delete_transactions_for_file(file_id)
        
        # Save new transactions to the database
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
        
        return transaction_count
    except Exception as e:
        logger.error(f"Error processing transactions: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error args: {e.args}")
        update_transaction_file(file_id, {
            'processingStatus': ProcessingStatus.ERROR,
            'errorMessage': f'Error processing transactions: {str(e)}'
        })
        return 0

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
        transaction_count = process_file_with_account(
            file_id=file_id,
            content_bytes=content_bytes,
            file_format=file_record.get('fileFormat', FileFormat.CSV),
            opening_balance=float(file_record.get('openingBalance', 0)),
            user_id=user_id,
            account_id=account_id
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': f'Successfully processed {transaction_count} transactions',
                'transactionCount': transaction_count
            })
        }
        
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

def extract_opening_balance(content_bytes: bytes, file_format: FileFormat) -> Optional[float]:
    """
    Extract the opening balance from file content based on its format.
    
    Args:
        content_bytes: The file content
        file_format: The detected file format
        
    Returns:
        Opening balance as float if found, None otherwise
    """
    try:
        # Convert bytes to string for text processing
        try:
            content_text = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            # For binary formats like OFX/QFX, try another encoding
            try:
                content_text = content_bytes.decode('latin-1')
            except UnicodeDecodeError:
                return None
        
        # Process based on file format
        if file_format == FileFormat.OFX or file_format == FileFormat.QFX:
            return extract_opening_balance_ofx(content_text)
        elif file_format == FileFormat.CSV:
            return extract_opening_balance_csv(content_text)
        
        return None
    except Exception as e:
        logger.error(f"Error extracting opening balance: {str(e)}")
        return None

def extract_opening_balance_ofx(content: str) -> Optional[float]:
    """
    Extract opening balance from OFX/QFX file.
    
    Args:
        content: File content as string
        
    Returns:
        Opening balance as float if found, None otherwise
    """
    # Look for opening balance in OFX format
    # Modern OFX (XML-like)
    match = re.search(r'<LEDGERBAL>.*?<BALAMT>([-+]?\d*\.?\d+)</BALAMT>', content, re.DOTALL)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            pass
    
    # SGML format OFX
    match = re.search(r'LEDGERBAL\s+BALAMT:([-+]?\d*\.?\d+)', content)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            pass
    
    # Some files have AVAILBAL (available balance) which can be used as a fallback
    match = re.search(r'<AVAILBAL>.*?<BALAMT>([-+]?\d*\.?\d+)</BALAMT>', content, re.DOTALL)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            pass
    
    return None

def extract_opening_balance_csv(content: str) -> Optional[float]:
    """
    Extract opening balance from CSV file.
    This is more heuristic as CSV formats vary widely by institution.
    
    Args:
        content: File content as string
        
    Returns:
        Opening balance as float if found, None otherwise
    """
    # Common patterns for opening balance in CSVs
    patterns = [
        r'opening\s+balance[^,]*,\s*([-+]?\d*\.?\d+)',  # "Opening Balance, 1000.00"
        r'beginning\s+balance[^,]*,\s*([-+]?\d*\.?\d+)', # "Beginning Balance, 1000.00"
        r'balance\s+forward[^,]*,\s*([-+]?\d*\.?\d+)',   # "Balance Forward, 1000.00"
        r'previous\s+balance[^,]*,\s*([-+]?\d*\.?\d+)'   # "Previous Balance, 1000.00"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, TypeError):
                continue
    
    # Look for potential header and first transaction
    lines = content.split('\n')
    if len(lines) >= 2:
        # Some institutions put the opening balance as the first transaction
        # Heuristic: Look for a row that contains words like "opening", "balance", "beginning"
        for i, line in enumerate(lines[:min(10, len(lines))]):
            if re.search(r'open|balanc|begin', line, re.IGNORECASE):
                # Try to extract any numbers from this line
                numbers = re.findall(r'([-+]?\d*\.?\d+)', line)
                for num in numbers:
                    try:
                        return float(num)
                    except (ValueError, TypeError):
                        continue
                        
    return None

def find_file_records_by_s3_key(s3_key: str) -> List[Dict[str, Any]]:
    """
    Find file records in DynamoDB that match the given S3 key.
    
    Args:
        s3_key: The S3 key to search for
        
    Returns:
        List of matching file records
    """
    try:
        # Query DynamoDB using the S3Key index
        response = file_table.query(
            IndexName='S3KeyIndex',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('s3Key').eq(s3_key)
        )
        
        files = response.get('Items', [])
        logger.info(f"Found {len(files)} file records for S3 key: {s3_key}")
        return files
    except Exception as e:
        logger.error(f"Error finding file records by S3 key: {str(e)}")
        return [] 