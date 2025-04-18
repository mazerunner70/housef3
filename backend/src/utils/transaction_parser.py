import csv
import io
import re
import logging
import xml.etree.ElementTree as ET
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from models.transaction_file import FileFormat
from models.field_map import FieldMap, FieldMapping
from utils.db_utils import create_transaction, delete_transactions_for_file, update_transaction_file
import decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def apply_field_mapping(row_data: Dict[str, Any], field_map: FieldMap) -> Dict[str, Any]:
    """
    Apply field mapping to a row of data.
    
    Args:
        row_data: Dictionary containing the raw row data
        field_map: FieldMap instance containing the mapping rules
        
    Returns:
        Dictionary with mapped fields
    """
    result = {}
    
    for mapping in field_map.mappings:
        source = mapping.source_field
        target = mapping.target_field
        
        if source not in row_data:
            logger.warning(f"Source field '{source}' not found in row data")
            continue
            
        value = row_data[source]
        
        # Apply transformation if specified
        if mapping.transformation:
            try:
                # For now, we only support basic Python expressions
                # In the future, this could be expanded to more complex transformations
                value = eval(mapping.transformation, {"value": value})
            except Exception as e:
                logger.error(f"Error applying transformation {mapping.transformation}: {str(e)}")
                continue
        
        result[target] = value
    
    return result

def parse_transactions(content: bytes, 
                      file_format: FileFormat, 
                      opening_balance: float,
                      field_map: Optional[FieldMap] = None) -> List[Dict[str, Any]]:
    """
    Parse transactions from file content based on the file format.
    
    Args:
        content: The raw file content
        file_format: The format of the file (CSV, OFX, etc.)
        opening_balance: The opening balance to use for running total calculation
        field_map: Optional field mapping configuration
        
    Returns:
        List of transaction dictionaries
    """
    if file_format == FileFormat.CSV:
        return parse_csv_transactions(content, opening_balance, field_map)
    elif file_format in [FileFormat.OFX, FileFormat.QFX]:
        return parse_ofx_transactions(content, opening_balance, field_map)
    else:
        logger.warning(f"Unsupported file format for transaction parsing: {file_format}")
        return []

def process_file_transactions(file_id: str, content_bytes: bytes, file_format: FileFormat, opening_balance: float, user_id: str) -> int:
    """
    Process a file to extract and save transactions.
    
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
        # Parse transactions using the utility
        transactions = parse_transactions(
            content_bytes, 
            file_format,
            opening_balance
        )
        
        # Delete existing transactions if any
        delete_transactions_for_file(file_id)
        
        # Save new transactions to the database
        transaction_count = 0
        for transaction_data in transactions:
            try:
                # Add the file_id and user_id to each transaction
                transaction_data['file_id'] = file_id
                transaction_data['user_id'] = user_id
                
                # Create and save the transaction
                create_transaction(transaction_data)
                transaction_count += 1
            except Exception as tx_error:
                logger.warning(f"Error creating transaction: {str(tx_error)}")
                
        logger.info(f"Saved {transaction_count} transactions for file {file_id}")
        
        # Update the file record with transaction count
        update_transaction_file(file_id, {
            'transactionCount': str(transaction_count)
        })
        
        return transaction_count
    except Exception as parse_error:
        logger.error(f"Error parsing transactions: {str(parse_error)}")
        return 0

def find_column_index(header: List[str], possible_names: List[str]) -> Optional[int]:
    """Find the index of a column given possible column names."""
    # Convert header to lowercase for case-insensitive comparison
    header_lower = [col.lower() for col in header]
    
    # Check for exact matches first
    for name in possible_names:
        name_lower = name.lower()
        if name_lower in header_lower:
            return header_lower.index(name_lower)
    
    # Check for partial matches
    for name in possible_names:
        name_lower = name.lower()
        for i, col in enumerate(header_lower):
            if name_lower in col:
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

def parse_csv_transactions(content: bytes, opening_balance: float, field_map: Optional[FieldMap] = None) -> List[Dict[str, Any]]:
    """
    Parse transactions from CSV file content.
    
    Args:
        content: The raw CSV file content
        opening_balance: The opening balance to use for running total calculation
        field_map: Optional field mapping configuration
        
    Returns:
        List of transaction dictionaries
    """
    try:
        # Decode the content
        text_content = content.decode('utf-8')
        
        # Parse CSV
        csv_reader = csv.reader(io.StringIO(text_content))
        
        # Get header row
        header = next(csv_reader, None)
        if not header:
            return []
            
        # If using field map, validate required fields are present
        if field_map:
            missing_fields = []
            for mapping in field_map.mappings:
                if mapping.source_field not in header:
                    missing_fields.append(mapping.source_field)
            
            if missing_fields:
                logger.error(f"Missing required fields in CSV: {missing_fields}")
                return []
        else:
            # Find columns by common names if no field map
            date_col = find_column_index(header, ['date', 'transaction date', 'posted date'])
            desc_col = find_column_index(header, ['description', 'payee', 'merchant', 'transaction'])
            amount_col = find_column_index(header, ['amount', 'transaction amount'])
            type_col = find_column_index(header, ['type', 'transaction type'])
            category_col = find_column_index(header, ['category', 'transaction category'])
            memo_col = find_column_index(header, ['memo', 'notes', 'description'])
            balance_col = find_column_index(header, ['balance', 'running balance'])
            
            if None in [date_col, desc_col, amount_col]:
                logger.error("Missing required columns in CSV")
                return []
        
        transactions = []
        running_total = Decimal(str(opening_balance))
        
        for row in csv_reader:
            try:
                if field_map:
                    # Apply field mapping
                    row_data = dict(zip(header, row))
                    mapped_data = apply_field_mapping(row_data, field_map)
                    
                    # Ensure required fields are present
                    if not all(key in mapped_data for key in ['date', 'description', 'amount']):
                        logger.warning("Missing required fields after mapping")
                        continue
                        
                    # Parse amount and calculate running total
                    amount = Decimal(str(mapped_data['amount']).replace(',', ''))
                    running_total += amount
                    
                    # Create transaction with mapped data
                    transaction = {
                        'date': mapped_data['date'],
                        'description': mapped_data['description'],
                        'amount': str(amount),
                        'balance': str(running_total)
                    }
                    
                    # Add optional fields if present in mapping
                    for field in ['transaction_type', 'category', 'memo']:
                        if field in mapped_data:
                            transaction[field] = mapped_data[field]
                            
                else:
                    # Parse without field mapping
                    date = parse_date(row[date_col].strip())
                    if not date:
                        logger.warning(f"Invalid date format: {row[date_col]}")
                        continue
                        
                    description = row[desc_col].strip()
                    if not description:
                        logger.warning("Empty description")
                        continue
                        
                    try:
                        amount = Decimal(str(row[amount_col]).replace(',', ''))
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid amount: {row[amount_col]}")
                        continue
                        
                    # Calculate running total
                    running_total += amount
                    
                    # Create transaction
                    transaction = {
                        'date': date,
                        'description': description,
                        'amount': str(amount),
                        'balance': str(running_total)
                    }
                    
                    # Add optional fields if available
                    if type_col is not None:
                        transaction['transaction_type'] = row[type_col].strip() or ('DEBIT' if amount < 0 else 'CREDIT')
                    if category_col is not None:
                        transaction['category'] = row[category_col].strip()
                    if memo_col is not None and memo_col != desc_col:
                        memo = row[memo_col].strip()
                        if memo and memo != description:
                            transaction['memo'] = memo
                
                transactions.append(transaction)
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Error parsing row: {str(e)}")
                continue
        
        return transactions
        
    except Exception as e:
        logger.error(f"Error parsing CSV file: {str(e)}")
        return []

def parse_ofx_transactions(content: bytes, opening_balance: float, field_map: Optional[FieldMap] = None) -> List[Dict[str, Any]]:
    """
    Parse transactions from OFX/QFX file content.
    
    Args:
        content: The raw OFX/QFX file content
        opening_balance: The opening balance to use for running total calculation
        field_map: Optional field mapping configuration
        
    Returns:
        List of transaction dictionaries
    """
    try:
        # Decode content
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            text_content = content.decode('latin-1')
            
        # Extract transaction sections - handle both XML and SGML formats
        transaction_blocks = []
        
        # Try XML format first
        xml_blocks = re.findall(r'<STMTTRN>(.*?)</STMTTRN>', text_content, re.DOTALL)
        if xml_blocks:
            transaction_blocks = xml_blocks
            is_xml = True
        else:
            # Try SGML format - match from STMTTRN to next blank line or end of file
            sgml_blocks = re.findall(r'STMTTRN\n(.*?)(?:\n\s*\n|\Z)', text_content, re.DOTALL)
            transaction_blocks = sgml_blocks
            is_xml = False
        
        transactions = []
        running_total = Decimal(str(opening_balance))
        
        for block in transaction_blocks:
            try:
                # Extract transaction details using appropriate patterns
                if is_xml:
                    date_match = re.search(r'<DTPOSTED>(.*?)</DTPOSTED>', block)
                    amount_match = re.search(r'<TRNAMT>(.*?)</TRNAMT>', block)
                    name_match = re.search(r'<(?:NAME|n)>(.*?)</(?:NAME|n)>', block)
                    memo_match = re.search(r'<MEMO>(.*?)</MEMO>', block)
                    type_match = re.search(r'<TRNTYPE>(.*?)</TRNTYPE>', block)
                else:
                    date_match = re.search(r'DTPOSTED:(\d+)', block)
                    amount_match = re.search(r'TRNAMT:([^\n]+)', block)
                    name_match = re.search(r'NAME:([^\n]+)', block)
                    memo_match = re.search(r'MEMO:([^\n]+)', block)
                    type_match = re.search(r'TRNTYPE:([^\n]+)', block)
                
                if not (date_match and amount_match):
                    logger.warning("Missing required fields in transaction block")
                    continue
                    
                # Parse date (format: YYYYMMDD)
                date_str = date_match.group(1).strip()
                if len(date_str) >= 8:
                    year = date_str[0:4]
                    month = date_str[4:6]
                    day = date_str[6:8]
                    date = f"{year}-{month}-{day}"
                else:
                    date = date_str
                        
                # Parse amount - clean up whitespace and handle negative signs
                amount_str = amount_match.group(1).strip()
                try:
                    amount = Decimal(amount_str)
                except decimal.InvalidOperation:
                    # Try cleaning the string
                    amount_str = re.sub(r'[^\d.-]', '', amount_str)
                    amount = Decimal(amount_str)
                
                # Get description from NAME or MEMO
                description = None
                if name_match:
                    description = name_match.group(1).strip()
                if not description and memo_match:
                    description = memo_match.group(1).strip()
                if not description:
                    description = "Unknown Transaction"
                    
                # Calculate running total
                running_total += amount
                
                # Create transaction
                transaction = {
                    'date': date,
                    'description': description,
                    'amount': str(amount),
                    'balance': str(running_total),
                    'transaction_type': type_match.group(1).strip() if type_match else ('DEBIT' if amount < 0 else 'CREDIT')
                }
                
                # Add memo if different from description
                if memo_match:
                    memo = memo_match.group(1).strip()
                    if memo and memo != description:
                        transaction['memo'] = memo
                
                transactions.append(transaction)
            except Exception as e:
                logger.error(f"Error parsing OFX transaction block: {str(e)}")
                continue
                
        return transactions
    except Exception as e:
        logger.error(f"Error parsing OFX transactions: {str(e)}")
        return [] 