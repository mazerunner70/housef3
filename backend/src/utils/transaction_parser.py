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
import decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

__all__ = [
    'parse_transactions',
    'parse_csv_transactions',
    'parse_ofx_transactions',
    'apply_field_mapping',
    'find_column_index',
    'parse_date',
    'detect_date_order'
]

def detect_date_order(dates: List[str]) -> str:
    """Detect if dates are in ascending or descending order."""
    if len(dates) < 2:
        return 'asc'  # Default to ascending if not enough dates
        
    # Convert dates to timestamps
    timestamps = []
    for date in dates:
        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d")
            timestamps.append(parsed_date.timestamp())
        except ValueError:
            continue
    if len(timestamps) < 2:
        return 'asc'  # Default to ascending if not enough valid dates
        
    # Find first non-equal pair of timestamps
    for i in range(1, len(timestamps)):
        if timestamps[i] != timestamps[i-1]:
            # Return 'desc' if later dates come first, 'asc' otherwise
            return 'desc' if timestamps[i] < timestamps[i-1] else 'asc'
            
    # If all timestamps are equal, default to ascending
    return 'asc'

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

def parse_date(date_str: str) -> Optional[int]:
    """Try to parse date string in various formats and return milliseconds since epoch."""
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
            dt = datetime.strptime(date_str, fmt)
            # Convert to milliseconds since epoch
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    
    return None

def parse_csv_transactions(content: bytes, opening_balance: Optional[float] = None, field_map: Optional[FieldMap] = None) -> List[Dict[str, Any]]:
    """
    Parse transactions from CSV file content.
    
    Args:
        content: The raw CSV file content
        opening_balance: Optional opening balance to use for running total calculation. Defaults to 0.00 if not provided.
        field_map: Optional field mapping configuration
        
    Returns:
        List of transaction dictionaries
    """
    def process_amount(amount: Decimal, debit_credit: Optional[str] = None) -> Decimal:
        """Process amount based on debit/credit indicator."""
        if debit_credit and debit_credit.upper() == 'DBIT':
            return -abs(amount)
        return amount

    try:
        # Decode the content
        text_content = content.decode('utf-8')
        
        # Create a custom dialect for handling unquoted fields with commas
        class UnquotedDialect(csv.Dialect):
            delimiter = ','
            quotechar = '"'
            doublequote = True
            skipinitialspace = True
            lineterminator = '\n'
            quoting = csv.QUOTE_MINIMAL
        
        # Parse CSV using custom dialect
        csv_file = io.StringIO(text_content)
        reader = csv.reader(csv_file, dialect=UnquotedDialect())
        
        # Get header row
        header = next(reader, None)
        if not header:
            return []
            
        # Clean up headers
        header = [h.strip() for h in header]
        
        # Find columns by common names if no field map
        if field_map:
            # Use field mapping to get column indices
            date_col = find_column_index(header, [m.source_field for m in field_map.mappings if m.target_field == 'date'])
            desc_col = find_column_index(header, [m.source_field for m in field_map.mappings if m.target_field == 'description'])
            amount_col = find_column_index(header, [m.source_field for m in field_map.mappings if m.target_field == 'amount'])
            debitOrCredit_col = find_column_index(header, [m.source_field for m in field_map.mappings if m.target_field == 'debitOrCredit'])
            category_col = find_column_index(header, [m.source_field for m in field_map.mappings if m.target_field == 'category'])
            memo_col = find_column_index(header, [m.source_field for m in field_map.mappings if m.target_field == 'memo'])
        else:
            # Use default column names
            date_col = find_column_index(header, ['date', 'transaction date', 'posted date'])
            desc_col = find_column_index(header, ['description', 'payee', 'merchant', 'transaction'])
            amount_col = find_column_index(header, ['amount', 'transaction amount', 'billing amount'])
            debitOrCredit_col = find_column_index(header, ['type', 'transaction type'])
            category_col = find_column_index(header, ['category', 'transaction category'])
            memo_col = find_column_index(header, ['memo', 'notes', 'reference'])
        
        # Validate required columns
        if date_col is None or desc_col is None or amount_col is None:
            raise ValueError("Missing required columns: Date, Description, or Amount")
        
        # Read all rows
        rows = list(reader)
        
        # Detect date order
        date_order = detect_date_order([row[date_col] for row in rows if len(row) > date_col])
        
        # Reverse rows if dates are in descending order
        if date_order == 'desc':
            rows.reverse()
            logger.info("Reversed transaction order to ascending")
            
        # Initialize balance
        balance = Decimal(str(opening_balance)) if opening_balance is not None else Decimal('0.00')
        
        # Process each row
        transactions = []
        for i, row in enumerate(rows):
            if len(row) <= max(date_col, desc_col, amount_col):
                continue
                
            # Create raw row data dictionary
            row_data = {
                'date': row[date_col],
                'description': row[desc_col],
                'amount': row[amount_col],
                'debitOrCredit': row[debitOrCredit_col] if debitOrCredit_col is not None and len(row) > debitOrCredit_col else None,
                'category': row[category_col] if category_col is not None and len(row) > category_col else None,
                'memo': row[memo_col] if memo_col is not None and len(row) > memo_col else None
            }
            logger.info(f"Row: {row}")
            logger.info(f"Row data: {row_data}")    

            # Process the amount
            raw_amount = Decimal(row_data['amount'].replace('$', '').replace(',', ''))
            processed_amount = process_amount(raw_amount, row_data.get('debitOrCredit'))
            
            # Update balance with processed amount
            balance += processed_amount
            
            # Create transaction dictionary
            transaction = {
                'date': parse_date(row_data['date']),
                'description': row_data['description'].strip(),
                'amount': processed_amount,  # Keep as Decimal
                'balance': balance,  # Keep as Decimal
                'import_order': i + 1,  # Add 1-based import order
                'transaction_type': row_data.get('debitOrCredit')  # Use debitOrCredit value for transaction_type
            }
            
            logger.info(f"Transaction: {transaction}")
            
            # Add optional fields
            if row_data.get('category'):
                transaction['category'] = row_data['category'].strip()
            if row_data.get('memo'):
                transaction['memo'] = row_data['memo'].strip()
                
            transactions.append(transaction)
            
        return transactions
        
    except Exception as e:
        logger.error(f"Error parsing CSV transactions: {str(e)}")
        return []

def parse_ofx_transactions(content: bytes, opening_balance: float, field_map: Optional[FieldMap] = None) -> List[Dict[str, Any]]:
    """
    Parse transactions from OFX/QFX file content.
    
    Args:
        content: The raw OFX/QFX file content
        opening_balance: Opening balance to use for running total calculation
        field_map: Optional field mapping configuration
        
    Returns:
        List of transaction dictionaries
    """
    try:
        # Decode the content
        text_content = content.decode('utf-8')
        
        # Strip OFX header if present
        if text_content.startswith('OFXHEADER:'):
            # Find the start of the XML content
            xml_start = text_content.find('<OFX>')
            if xml_start != -1:
                # XML format
                text_content = text_content[xml_start:]
                return parse_ofx_xml(text_content, opening_balance)
            else:
                # Colon-separated format
                return parse_ofx_colon_separated(text_content, opening_balance)
        else:
            # Try parsing as XML
            try:
                return parse_ofx_xml(text_content, opening_balance)
            except ET.ParseError:
                # Try parsing as colon-separated
                return parse_ofx_colon_separated(text_content, opening_balance)
        
    except Exception as e:
        logger.error(f"Error parsing OFX transactions: {str(e)}")
        return []

def parse_ofx_xml(text_content: str, opening_balance: float) -> List[Dict[str, Any]]:
    """Parse OFX content in XML format."""
    root = ET.fromstring(text_content)
    transactions = []
    balance = Decimal(str(opening_balance))
    
    for i, stmttrn in enumerate(root.findall('.//STMTTRN')):
        # Extract transaction details
        date = stmttrn.find('DTPOSTED').text
        amount = Decimal(stmttrn.find('TRNAMT').text)
        # Try both NAME and n elements for description
        name = stmttrn.find('NAME')
        if name is None:
            name = stmttrn.find('n')
        name = name.text if name is not None else ''
        memo = stmttrn.find('MEMO').text if stmttrn.find('MEMO') is not None else ''
        trntype = stmttrn.find('TRNTYPE').text if stmttrn.find('TRNTYPE') is not None else 'DEBIT'
        
        # Create transaction dictionary
        transaction = {
            'date': parse_date(date),
            'description': name.strip(),
            'amount': amount,  # Keep as Decimal
            'balance': balance + amount,  # Keep as Decimal
            'transaction_type': trntype.strip().upper(),
            'memo': memo.strip(),
            'import_order': i + 1  # Add 1-based import order
        }
        
        # Update balance
        balance += amount
        
        transactions.append(transaction)
    
    return transactions

def parse_ofx_colon_separated(text_content: str, opening_balance: float) -> List[Dict[str, Any]]:
    """Parse OFX content in colon-separated format."""
    transactions = []
    balance = Decimal(str(opening_balance))
    current_transaction = {}
    in_transaction = False
    import_order = 1  # Initialize import order counter
    
    for line in text_content.splitlines():
        line = line.strip()
        if not line:
            continue
            
        if line == 'STMTTRN':
            if in_transaction and current_transaction:
                # Add the previous transaction
                transaction = {
                    'date': parse_date(current_transaction.get('DTPOSTED', '')),
                    'description': current_transaction.get('NAME', '').strip(),
                    'amount': Decimal(current_transaction.get('TRNAMT', '0')),  # Keep as Decimal
                    'balance': balance + Decimal(current_transaction.get('TRNAMT', '0')),  # Keep as Decimal
                    'transaction_type': current_transaction.get('TRNTYPE', 'DEBIT').strip().upper(),
                    'memo': current_transaction.get('MEMO', '').strip(),
                    'import_order': import_order  # Add import order
                }
                transactions.append(transaction)
                balance += Decimal(current_transaction.get('TRNAMT', '0'))
                current_transaction = {}
                import_order += 1  # Increment import order counter
            in_transaction = True
        elif in_transaction and ':' in line:
            key, value = line.split(':', 1)
            current_transaction[key] = value.strip()
    
    # Add the last transaction if we have one
    if in_transaction and current_transaction:
        transaction = {
            'date': parse_date(current_transaction.get('DTPOSTED', '')),
            'description': current_transaction.get('NAME', '').strip(),
            'amount': Decimal(current_transaction.get('TRNAMT', '0')),  # Keep as Decimal
            'balance': balance + Decimal(current_transaction.get('TRNAMT', '0')),  # Keep as Decimal
            'transaction_type': current_transaction.get('TRNTYPE', 'DEBIT').strip().upper(),
            'memo': current_transaction.get('MEMO', '').strip(),
            'import_order': import_order  # Add import order
        }
        transactions.append(transaction)
    
    return transactions 