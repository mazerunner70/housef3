"""
Utility functions for processing transaction files.
"""
import logging
import os
import re
import uuid
from models.transaction import Transaction
import boto3
from boto3.dynamodb.conditions import Key
from typing import Dict, Any, List, Optional
from decimal import Decimal
from models.transaction_file import FileFormat
from utils.db_utils import (
    _get_transaction_file,  # Internal use - called after auth checks
    check_duplicate_transaction
)
from utils.s3_dao import get_object_content

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
dynamodb = boto3.resource('dynamodb')

# Get table names from environment variables
TRANSACTIONS_TABLE = os.environ.get('TRANSACTIONS_TABLE', 'transactions')
FILES_TABLE = os.environ.get('FILES_TABLE', 'transaction-files')

# Initialize DynamoDB tables
transaction_table = dynamodb.Table(TRANSACTIONS_TABLE)
file_table = dynamodb.Table(FILES_TABLE)

def create_composite_key(user_id: str, transaction: Dict[str, Any]) -> str:
    """Create a composite key for a transaction.
    
    Args:
        user_id: The user ID
        transaction: The transaction dictionary
        
    Returns:
        str: The composite key
    """
    amount = transaction['amount']
    return f"{user_id}#{transaction['date']}#{amount}#{transaction['description']}"

def get_file_content(file_id: uuid.UUID, s3_client: Any = None) -> Optional[bytes]:
    """
    Get file content from S3.
    
    Args:
        file_id: ID of the file to retrieve
        s3_client: Optional S3 client for testing
        
    Returns:
        File content as bytes if found, None otherwise
    """
    try:
        # Get the file record to find the S3 key
        file_record = _get_transaction_file(file_id)
        if not file_record or not file_record.s3_key:
            logger.error(f"File record or S3 key not found for ID: {file_id}")
            return None
            
        # Use s3_dao to get file content
        return get_object_content(file_record.s3_key)
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
            KeyConditionExpression=Key('s3Key').eq(s3_key)
        )
        
        files = response.get('Items', [])
        logger.info(f"Found {len(files)} file records for S3 key: {s3_key}")
        return files
    except Exception as e:
        logger.error(f"Error finding file records by S3 key: {str(e)}")
        return []

def extract_opening_balance(content_bytes: bytes, file_format: FileFormat) -> Optional[Decimal]:
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
        if type(file_format).__name__ == "FileFormat" and file_format.name in ["OFX", "QFX"]:
            return extract_opening_balance_ofx(content_text)
        elif type(file_format).__name__ == "FileFormat" and file_format.name == "CSV":
            return extract_opening_balance_csv(content_text)
        
        return None
    except Exception as e:
        logger.error(f"Error extracting opening balance: {str(e)}")
        return None

def extract_opening_balance_ofx(content: str) -> Optional[Decimal]:
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
            return Decimal(match.group(1))
        except (ValueError, TypeError):
            pass
    
    # SGML format OFX
    match = re.search(r'LEDGERBAL\s+BALAMT:([-+]?\d*\.?\d+)', content)
    if match:
        try:
            return Decimal(match.group(1))
        except (ValueError, TypeError):
            pass
    
    # Some files have AVAILBAL (available balance) which can be used as a fallback
    match = re.search(r'<AVAILBAL>.*?<BALAMT>([-+]?\d*\.?\d+)</BALAMT>', content, re.DOTALL)
    if match:
        try:
            return Decimal(match.group(1))
        except (ValueError, TypeError):
            pass
    
    return None

def extract_opening_balance_csv(content: str) -> Optional[Decimal]:
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
                return Decimal(match.group(1))
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
                        return Decimal(num)
                    except (ValueError, TypeError):
                        continue
                        
    return None 

def calculate_opening_balance_from_duplicates(transactions: List[Transaction]) -> Optional[Decimal]:
    """
    Calculate opening balance by checking if first or last transaction is a duplicate.
    
    Args:
        transactions: List of parsed transactions
        
    Returns:
        Decimal: Calculated opening balance if found, None otherwise
    """
    if not transactions:
        return None
        
    try:
        # Check first transaction
        first_tx = transactions[0]
        logger.info(f"Checking first transaction: {first_tx}")
        if check_duplicate_transaction(first_tx) and first_tx.balance:
            # If first transaction is duplicate, use its balance
            logger.info(f"First transaction is duplicate, using balance: {first_tx.balance}")
            return first_tx.balance
            
        # Check last transaction
        last_tx = transactions[-1]
        logger.info(f"Checking last transaction: {last_tx}")
        if check_duplicate_transaction(last_tx) and last_tx.balance and all(tx.amount for tx in transactions):
            # If last transaction is duplicate, calculate opening balance
            # by subtracting all transaction amounts from the matched balance
            total_amount = sum(tx.amount for tx in transactions)
            res = last_tx.balance - total_amount
            logger.info(f"Last transaction is duplicate, calculated opening balance: {res}")
            return res
        return None
    except Exception as e:
        logger.error(f"Error calculating opening balance from duplicates: {str(e)}")
        return None 