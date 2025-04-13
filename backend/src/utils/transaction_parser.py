import csv
import io
import re
import logging
import xml.etree.ElementTree as ET
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from models.transaction_file import FileFormat

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def parse_transactions(content: bytes, 
                      file_format: FileFormat, 
                      opening_balance: float) -> List[Dict[str, Any]]:
    """
    Parse transactions from file content based on the file format.
    
    Args:
        content: The raw file content
        file_format: The format of the file (CSV, OFX, etc.)
        opening_balance: The opening balance to use for running total calculation
        
    Returns:
        List of transaction dictionaries
    """
    if file_format == FileFormat.CSV:
        return parse_csv_transactions(content, opening_balance)
    elif file_format in [FileFormat.OFX, FileFormat.QFX]:
        return parse_ofx_transactions(content, opening_balance)
    else:
        logger.warning(f"Unsupported file format for transaction parsing: {file_format}")
        return []

def find_column_index(header: List[str], possible_names: List[str]) -> Optional[int]:
    """Find the index of a column given possible column names."""
    for name in possible_names:
        for i, col in enumerate(header):
            if name.lower() in col.lower():
                return i
    return None

def parse_date(date_str: str) -> Optional[str]:
    """Try to parse date string in various formats."""
    date_formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y%m%d",
        "%m-%d-%Y",
        "%d-%m-%Y"
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return None

def parse_csv_transactions(content: bytes, opening_balance: float) -> List[Dict[str, Any]]:
    """
    Parse transactions from CSV file content.
    
    Args:
        content: The raw CSV file content
        opening_balance: The opening balance to use for running total calculation
        
    Returns:
        List of transaction dictionaries
    """
    try:
        # Decode the content
        text_content = content.decode('utf-8')
        
        # Parse CSV
        csv_reader = csv.reader(io.StringIO(text_content))
        
        # Try to determine the header row and column mappings
        header = next(csv_reader, None)
        if not header:
            return []
            
        # Try to identify column positions
        date_col = find_column_index(header, ['date', 'transaction date', 'posted date'])
        desc_col = find_column_index(header, ['description', 'payee', 'memo', 'note'])
        amount_col = find_column_index(header, ['amount', 'transaction amount'])
        
        if date_col is None or desc_col is None or amount_col is None:
            logger.warning("Could not identify required columns in CSV file")
            return []
            
        # Parse transactions
        transactions = []
        running_total = opening_balance
        
        for row in csv_reader:
            if len(row) <= max(date_col, desc_col, amount_col):
                continue  # Skip rows that don't have enough columns
                
            try:
                # Parse date
                date_str = row[date_col].strip()
                date = parse_date(date_str)
                if not date:
                    continue
                    
                # Parse description
                description = row[desc_col].strip()
                if not description:
                    continue
                    
                # Parse amount
                amount_str = row[amount_col].strip().replace('$', '').replace(',', '')
                amount = float(amount_str)
                
                # Calculate running total
                running_total += amount
                
                # Create transaction dictionary
                transaction = {
                    'date': date,
                    'description': description,
                    'amount': amount,
                    'running_total': running_total
                }
                
                # Add optional fields if they exist
                type_col = find_column_index(header, ['type', 'transaction type'])
                if type_col is not None and len(row) > type_col:
                    transaction['transaction_type'] = row[type_col].strip()
                    
                category_col = find_column_index(header, ['category', 'classification'])
                if category_col is not None and len(row) > category_col:
                    transaction['category'] = row[category_col].strip()
                    
                memo_col = find_column_index(header, ['memo', 'notes', 'comments'])
                if memo_col is not None and len(row) > memo_col:
                    transaction['memo'] = row[memo_col].strip()
                
                transactions.append(transaction)
            except Exception as e:
                logger.warning(f"Error parsing CSV row: {str(e)}")
                continue
                
        return transactions
    except Exception as e:
        logger.error(f"Error parsing CSV transactions: {str(e)}")
        return []

def parse_ofx_transactions(content: bytes, opening_balance: float) -> List[Dict[str, Any]]:
    """
    Parse transactions from OFX/QFX file content.
    
    Args:
        content: The raw OFX/QFX file content
        opening_balance: The opening balance to use for running total calculation
        
    Returns:
        List of transaction dictionaries
    """
    try:
        # Decode content
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            text_content = content.decode('latin-1')
            
        # Check if it's SGML or XML format
        if '<OFX>' in text_content:
            # It's XML-like, try to parse with ElementTree
            return parse_xml_ofx(text_content, opening_balance)
        else:
            # It's SGML-like, use regex to extract transactions
            return parse_sgml_ofx(text_content, opening_balance)
    except Exception as e:
        logger.error(f"Error parsing OFX transactions: {str(e)}")
        return []

def parse_xml_ofx(content: str, opening_balance: float) -> List[Dict[str, Any]]:
    """Parse XML-like OFX content."""
    transactions = []
    running_total = opening_balance
    
    try:
        # Extract transaction sections
        transaction_blocks = re.findall(r'<STMTTRN>(.*?)</STMTTRN>', content, re.DOTALL)
        
        for block in transaction_blocks:
            try:
                # Extract transaction details using regex
                date_match = re.search(r'<DTPOSTED>(.*?)</DTPOSTED>', block)
                amount_match = re.search(r'<TRNAMT>(.*?)</TRNAMT>', block)
                name_match = re.search(r'<NAME>(.*?)</NAME>', block) or re.search(r'<MEMO>(.*?)</MEMO>', block)
                memo_match = re.search(r'<MEMO>(.*?)</MEMO>', block)
                type_match = re.search(r'<TRNTYPE>(.*?)</TRNTYPE>', block)
                
                if date_match and amount_match and name_match:
                    # Parse date (format: YYYYMMDD)
                    date_str = date_match.group(1)
                    if len(date_str) >= 8:
                        year = date_str[0:4]
                        month = date_str[4:6]
                        day = date_str[6:8]
                        date = f"{year}-{month}-{day}"
                    else:
                        date = date_str
                        
                    # Parse amount
                    amount = float(amount_match.group(1))
                    
                    # Calculate running total
                    running_total += amount
                    
                    # Create transaction
                    transaction = {
                        'date': date,
                        'description': name_match.group(1),
                        'amount': amount,
                        'running_total': running_total
                    }
                    
                    # Add optional fields
                    if memo_match and memo_match.group(1) != name_match.group(1):
                        transaction['memo'] = memo_match.group(1)
                        
                    if type_match:
                        transaction['transaction_type'] = type_match.group(1)
                        
                    transactions.append(transaction)
            except Exception as e:
                logger.warning(f"Error parsing OFX transaction block: {str(e)}")
                continue
                
        return transactions
    except Exception as e:
        logger.error(f"Error parsing XML OFX: {str(e)}")
        return []

def parse_sgml_ofx(content: str, opening_balance: float) -> List[Dict[str, Any]]:
    """Parse SGML-like OFX content."""
    transactions = []
    running_total = opening_balance
    
    try:
        # Split content into lines and find transaction blocks
        lines = content.split('\n')
        current_transaction = {}
        
        for line in lines:
            line = line.strip()
            
            # Start of new transaction
            if line == 'STMTTRN':
                if current_transaction:
                    try:
                        # Process completed transaction
                        if all(k in current_transaction for k in ['date', 'amount', 'description']):
                            # Calculate running total
                            running_total += current_transaction['amount']
                            current_transaction['running_total'] = running_total
                            transactions.append(current_transaction)
                    except Exception as e:
                        logger.warning(f"Error processing transaction: {str(e)}")
                current_transaction = {}
                continue
            
            # Skip empty lines and header lines
            if not line or ':' not in line or line.startswith('OFXHEADER:'):
                continue
            
            try:
                # Parse key-value pairs
                key, value = line.split(':', 1)
                
                if key == 'DTPOSTED':
                    # Parse date (format: YYYYMMDD)
                    if len(value) >= 8:
                        year = value[0:4]
                        month = value[4:6]
                        day = value[6:8]
                        current_transaction['date'] = f"{year}-{month}-{day}"
                elif key == 'TRNAMT':
                    current_transaction['amount'] = float(value)
                elif key == 'NAME':
                    current_transaction['description'] = value
                elif key == 'MEMO':
                    current_transaction['memo'] = value
                elif key == 'TRNTYPE':
                    current_transaction['transaction_type'] = value
            except Exception as e:
                logger.warning(f"Error parsing line '{line}': {str(e)}")
                continue
        
        # Process the last transaction if exists
        if current_transaction:
            try:
                if all(k in current_transaction for k in ['date', 'amount', 'description']):
                    running_total += current_transaction['amount']
                    current_transaction['running_total'] = running_total
                    transactions.append(current_transaction)
            except Exception as e:
                logger.warning(f"Error processing last transaction: {str(e)}")
        
        return transactions
    except Exception as e:
        logger.error(f"Error parsing SGML OFX: {str(e)}")
        return [] 