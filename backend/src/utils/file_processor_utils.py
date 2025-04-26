"""
Utility functions for processing transaction files.
"""
import logging
import os
import re
from models.transaction import Transaction
import boto3
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime

from models.transaction_file import FileFormat, ProcessingStatus
from models.field_map import FieldMap
from utils.transaction_parser import parse_transactions
from utils.db_utils import (
    get_transaction_file,
    update_transaction_file,
    create_transaction,
    delete_transactions_for_file,
    get_field_map,
    get_account_default_field_map
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')

# Get table names from environment variables
TRANSACTIONS_TABLE = os.environ.get('TRANSACTIONS_TABLE', 'transactions')
FILES_TABLE = os.environ.get('FILES_TABLE', 'transaction-files')

# Initialize DynamoDB tables
transaction_table = dynamodb.Table(TRANSACTIONS_TABLE)
file_table = dynamodb.Table(FILES_TABLE)

def check_duplicate_transaction(transaction: Dict[str, Any], account_id: str) -> bool:
    """Check if a transaction already exists for the given account using numeric hash.
    
    Args:
        transaction: Dictionary containing transaction details
        account_id: ID of the account to check for duplicates
        
    Returns:
        bool: True if duplicate found, False otherwise
    """
    try:
        # Generate the same hash that would be stored with the transaction
        transaction_hash = Transaction.generate_transaction_hash(
            account_id,
            transaction['date'],
            Decimal(str(transaction['amount'])),  # Ensure amount is Decimal
            transaction['description']
        )
        
        # Query DynamoDB using the account ID and hash
        response = transaction_table.query(
            IndexName='TransactionHashIndex',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('accountId').eq(account_id) & 
                                 boto3.dynamodb.conditions.Key('transactionHash').eq(transaction_hash)
        )
        
        return len(response.get('Items', [])) > 0
    except Exception as e:
        logger.error(f"Error checking for duplicate transaction: {str(e)}")
        # If there's an error checking for duplicates, return False to allow the transaction
        return False

def create_composite_key(user_id: str, transaction: Dict[str, Any]) -> str:
    """Create a composite key for a transaction.
    
    Args:
        user_id: The user ID
        transaction: The transaction dictionary
        
    Returns:
        str: The composite key
    """
    amount = Decimal(str(transaction['amount']))
    return f"{user_id}#{transaction['date']}#{amount}#{transaction['description']}"

def get_file_content(file_id: str, s3_client: Any = None) -> Optional[bytes]:
    """
    Get file content from S3.
    
    Args:
        file_id: ID of the file to retrieve
        s3_client: Optional S3 client for testing
        
    Returns:
        File content as bytes if found, None otherwise
    """
    try:
        # Use provided client or default to s3_client
        s3_client = s3_client or s3_client
        
        # Get the file record to find the S3 key
        file_record = get_transaction_file(file_id)
        if not file_record or not file_record.s3_key:
            logger.error(f"File record or S3 key not found for ID: {file_id}")
            return None
            
        # Get the file content from S3
        response = s3_client.get_object(
            Bucket=os.environ.get('FILE_STORAGE_BUCKET'),
            Key=file_record.s3_key
        )
        return response['Body'].read()
    except Exception as e:
        logger.error(f"Error getting file content: {str(e)}")
        return None

def find_file_records_by_s3_key(s3_key: str, table: Any = None) -> List[Dict[str, Any]]:
    """
    Find file records in DynamoDB that match the given S3 key.
    
    Args:
        s3_key: The S3 key to search for
        table: Optional DynamoDB table for testing
        
    Returns:
        List of matching file records
    """
    try:
        # Use provided table or default to file_table
        table = table or file_table
        
        # Query DynamoDB using the S3Key index
        response = table.query(
            IndexName='S3KeyIndex',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('s3Key').eq(s3_key)
        )
        
        files = response.get('Items', [])
        logger.info(f"Found {len(files)} file records for S3 key: {s3_key}")
        return files
    except Exception as e:
        logger.error(f"Error finding file records by S3 key: {str(e)}")
        return []

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

def calculate_opening_balance_from_duplicates(transactions: List[Dict[str, Any]], account_id: str) -> Optional[Decimal]:
    """
    Calculate opening balance by checking if first or last transaction is a duplicate.
    
    Args:
        transactions: List of parsed transactions
        account_id: ID of the account to check for duplicates
        
    Returns:
        Decimal: Calculated opening balance if found, None otherwise
    """
    if not transactions:
        return None
        
    try:
        # Check first transaction
        first_tx = transactions[0]
        if check_duplicate_transaction(first_tx, account_id):
            # If first transaction is duplicate, use its balance
            return Decimal(str(first_tx['balance']))
            
        # Check last transaction
        last_tx = transactions[-1]
        if check_duplicate_transaction(last_tx, account_id):
            # If last transaction is duplicate, calculate opening balance
            # by subtracting all transaction amounts from the matched balance
            total_amount = sum(Decimal(str(tx['amount'])) for tx in transactions)
            return Decimal(str(last_tx['balance'])) - total_amount
            
        return None
    except Exception as e:
        logger.error(f"Error calculating opening balance from duplicates: {str(e)}")
        return None 