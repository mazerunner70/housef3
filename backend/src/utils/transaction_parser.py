import csv
import io
import re
import logging
import logging.config
import os
from unittest import mock
import xml.etree.ElementTree as ET
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from models.account import Currency
from models.money import Money
from models.transaction import Transaction
from models.transaction_file import FileFormat, TransactionFile
from models.file_map import FileMap, FieldMapping
import decimal

from utils.db_utils import checked_mandatory_file_map

# Configure logging
log_conf = os.environ.get('LOGGING_CONFIG')
if log_conf:
    logging.config.fileConfig(log_conf)
else:
    logging.basicConfig(
        level=os.environ.get('LOG_LEVEL', 'INFO'),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

# Get logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

__all__ = [
    'parse_transactions',
    'parse_csv_transactions',
    'parse_ofx_transactions',
    'apply_field_mapping',
    'find_column_index',
    'parse_date',
    'detect_date_order',
    'file_type_selector',
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

def apply_field_mapping(row_data: Dict[str, Any], field_map: FileMap) -> Dict[str, Any]:
    """
    Apply field mapping to a row of data.
    
    Args:
        row_data: Dictionary containing the raw row data
        field_map: FieldMap instance containing the mapping rules
        
    Returns:
        Dictionary with mapped fields
    """
    logger.info(f"Applying field mapping to row data: {row_data}")
    logger.info(f"Field map: {field_map.mappings}")
    result = {}
    
    for mapping in field_map.mappings:
        source = mapping.source_field
        target = mapping.target_field
        
        logger.info(f"Processing mapping: {source} -> {target}")
        
        if source not in row_data:
            logger.warning(f"Source field '{source}' not found in row data")
            continue
            
        value = row_data[source]
        logger.info(f"Raw value for {source}: {value}")
        
        # Apply transformation if specified
        if mapping.transformation:
            try:
                logger.info(f"Applying transformation: {mapping.transformation}")
                # For now, we only support basic Python expressions
                # In the future, this could be expanded to more complex transformations
                value = eval(mapping.transformation, {"value": value})
                logger.info(f"Transformed value: {value}")
            except Exception as e:
                logger.error(f"Error applying transformation {mapping.transformation}: {str(e)}")
                continue
        
        result[target] = value
    
    logger.info(f"Final mapped result: {result}")
    return result

def parse_transactions(transaction_file: TransactionFile,
                      content: bytes) -> Optional[List[Transaction]]:
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
    if transaction_file.file_map_id:
        if transaction_file.file_format == FileFormat.CSV:
            return parse_csv_transactions(transaction_file, content)
        elif transaction_file.file_format in [FileFormat.OFX, FileFormat.QFX]:
            return parse_ofx_transactions(transaction_file, content)
        else:
            logger.warning(f"Unsupported file format for transaction parsing: {transaction_file.file_format}")
            return []
    else: 
        logger.warning(f"File map is required for transaction parsing: {transaction_file.file_map_id}")
        return None

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

def parse_date(date_str: str) -> int:
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
    raise ValueError(f"Invalid date format: {date_str}")

def preprocess_csv_text(text_content: str) -> str:
    """
    Preprocess CSV text to fix rows with more columns than the other rows, due to the description having unquoted commas.
    Merges columns where a likely description field contains unquoted commas, quoting the merged field.
    Also removes trailing commas from all lines.
    """
    # Split the text into lines
    lines = text_content.splitlines()
    if not lines:
        return text_content
        
    # Parse the header to determine the expected number of fields
    header_line = lines[0].rstrip(",")  # Remove trailing commas from header
    # Use csv module to correctly parse the header
    reader = csv.reader([header_line])
    header_fields = next(reader)
    # count header fields excluding empty ones at the end
    expected_fields = len(header_fields)
    
    # Function to safely parse a line with the csv module
    def parse_csv_line(line):
        reader = csv.reader([line])
        try:
            return next(reader)
        except StopIteration:
            return []
    
    # Find the description column index
    desc_col = -1
    for i, field in enumerate(header_fields):
        field_lower = field.lower()
        # Exclude date-related fields from description matching
        if 'date' in field_lower:
            continue
        # Look for description-related fields
        if any(name in field_lower for name in ['description', 'payee', 'merchant', 'transaction']):
            desc_col = i
            break
            
    if desc_col == -1:
        desc_col = 1  # Default to second column if no description column found
        
    # Process each line
    fixed_lines = [header_line]  # Use the cleaned header line
    
    for i in range(1, len(lines)):
        line = lines[i].rstrip(",")  # Remove trailing commas from data lines
        if not line.strip():
            continue  # Skip empty lines
            
        # Parse the line
        fields = parse_csv_line(line)
        
        # If field count matches expected, keep it as is
        if len(fields) == expected_fields:
            fixed_lines.append(line)
            continue
            
        # If we have more fields than expected, we need to merge excess fields into the description
        if len(fields) > expected_fields:
            excess = len(fields) - expected_fields
            
            # Merge the description field with the excess fields
            before_desc = fields[:desc_col]
            desc_with_excess = fields[desc_col:desc_col+excess+1]
            merged_desc = ','.join(desc_with_excess)
            

                
            after_desc = fields[desc_col+excess+1:] if desc_col+excess+1 < len(fields) else []
            
            # Create a new row with the fixed fields
            new_fields = before_desc + [merged_desc] + after_desc
            
            # We need to format the line for CSV properly, so use a writer
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(new_fields)
            fixed_line = output.getvalue().strip()
            fixed_lines.append(fixed_line)
        else:
            # If fewer fields than expected (shouldn't happen), just keep as is
            fixed_lines.append(line)
            
    return '\n'.join(fixed_lines)

def parse_csv_transactions(transaction_file: TransactionFile, content: bytes) -> Optional[List[Transaction]]:
    """
    Parse transactions from CSV file content.
    
    Args:
        content: The raw CSV file content
        
    Returns:
        List of Transaction objects
    """
    def process_amount(amount: Decimal, currency: Optional[Currency], debit_credit: Optional[str] = None) -> Money:
        """Process amount based on debit/credit indicator."""
        if debit_credit and debit_credit.upper() == 'DBIT':
            return Money(-abs(amount), currency)
        return Money(amount, currency)
    
    try:
        if not transaction_file.file_map_id:
            return None
        file_map = checked_mandatory_file_map(transaction_file.file_map_id, transaction_file.user_id)
        # Decode the content
        raw_content = content.decode('utf-8')
        # Preprocess CSV text to fix unquoted commas
        text_content = preprocess_csv_text(raw_content)
        if len(text_content.splitlines()) != len(raw_content.splitlines()):
            raise ValueError("Preprocessing CSV text resulted in a different number of lines")
        # Create a custom dialect for handling quoted fields (after preprocessing)
        class QuotedDialect(csv.Dialect):
            delimiter = ','
            quotechar = '"'
            doublequote = True
            skipinitialspace = True
            lineterminator = '\n'
            quoting = csv.QUOTE_MINIMAL
        # Parse CSV using the updated dialect
        csv_file = io.StringIO(text_content)
        reader = csv.reader(csv_file, dialect=QuotedDialect())
        
        # Get header row
        header = next(reader, None)
        if not header:
            return []
            
        # Clean up headers
        header = [h.strip() for h in header]
        
        # Find columns by common names if no field map

        # Use field mapping to get column indices
        date_col = find_column_index(header, [m.source_field for m in file_map.mappings if m.target_field == 'date'])
        desc_col = find_column_index(header, [m.source_field for m in file_map.mappings if m.target_field == 'description'])
        amount_col = find_column_index(header, [m.source_field for m in file_map.mappings if m.target_field == 'amount'])
        debitOrCredit_col = find_column_index(header, [m.source_field for m in file_map.mappings if m.target_field == 'debitOrCredit'])
        category_col = find_column_index(header, [m.source_field for m in file_map.mappings if m.target_field == 'category'])
        memo_col = find_column_index(header, [m.source_field for m in file_map.mappings if m.target_field == 'memo'])
        currency_col = find_column_index(header, [m.source_field for m in file_map.mappings if m.target_field == 'currency'])
        # Validate required columns
        if date_col is None or desc_col is None or amount_col is None:
            raise ValueError("Missing required columns: Date, Description or Amount")
        
        # Read all rows
        rows = list(reader)
        logger.info(f"Rows count: {len(rows)}")
        if len(rows) != len(raw_content.splitlines())-1:
            raise ValueError(f"Number of rows in CSV file ({len(rows)}) does not match the number of lines in the raw content ({len(raw_content.splitlines())-1})")
        # Detect date order
        date_order = detect_date_order([row[date_col] for row in rows if len(row) > date_col])
        
        # Reverse rows if dates are in descending order
        if date_order == 'desc':
            rows.reverse()
            logger.info("Reversed transaction order to ascending")
            
        # Initialize balance
        if not transaction_file.account_id:
            raise ValueError("Account ID is required")
        if not transaction_file.user_id:
            raise ValueError("User ID is required")
        if not transaction_file.file_id:
            raise ValueError("File ID is required")
        balance: Money = transaction_file.opening_balance if transaction_file.opening_balance else Money(Decimal(0), transaction_file.currency)

        # Process each row
        transactions = []
        for i, row in enumerate(rows):
            if len(row) <= max(date_col, desc_col, amount_col):
                        continue
                        
            # Create raw row data dictionary
            row_dict = dict(zip(header, row))
            logger.info(f"Header: {header}")
            logger.info(f"Row: {row}")
            logger.info(f"Created row dict: {row_dict}")
            row_data = apply_field_mapping(row_dict, file_map)
            logger.info(f"After field mapping: {row_data}")
            if not row_data:
                logger.warning("Field mapping returned empty result")
                continue
            logger.info(f"in: Row: {row}")
            logger.info(f"out: Row data: {row_data}")    
            if balance.currency and row_data.get('currency') != balance.currency:
                raise ValueError(f"Currency mismatch: {row_data.get('currency')} != {balance.currency}")
            # Process the amount
            try:
                logger.info(f"Processing amount: {row_data['amount']}")
                raw_amount = Decimal(str(row_data['amount']))
                logger.info(f"Raw amount: {raw_amount}")
                processed_amount = process_amount(raw_amount, balance.currency, row_data.get('debitOrCredit'))
                logger.info(f"Processed amount: {processed_amount}")
            except (decimal.InvalidOperation, KeyError) as e:
                logger.error(f"Error processing amount: {str(e)}")
                continue
            
            # Update balance with processed amount
            balance += processed_amount
                    
            # Create transaction dictionary
            transaction = Transaction.create(
                account_id=transaction_file.account_id,
                user_id=transaction_file.user_id,
                file_id=transaction_file.file_id,    
                date=parse_date(row_data['date']),
                description=row_data['description'].strip(),
                amount=processed_amount,  
                balance=balance,  
                import_order=i + 1,  # Add 1-based import order
                transaction_type= row_data.get('debitOrCredit'),  # Use debitOrCredit value for transaction_type
                memo=row_data.get('memo'),
                check_number=row_data.get('checkNumber'),
                fit_id=row_data.get('fitId'),
                status=row_data.get('status')
            )
            
            logger.info(f"Transaction: {transaction}")

                
            transactions.append(transaction)
        
        return transactions
        
    except Exception as e:
        logger.error(f"Error parsing CSV transactions: {str(e)}")
        return []

def parse_ofx_colon_separated(text_content: str, transaction_file: TransactionFile) -> List[Transaction]:
    """Parse OFX content in colon-separated format."""
    transactions: List[Transaction] = []
    if not transaction_file.opening_balance:
        raise ValueError("Opening balance is required")
    balance: Money = transaction_file.opening_balance
    current_transaction: Dict[str, str] = {}
    in_transaction: bool = False
    import_order: int = 1
    
    logger.info("Parsing colon-separated OFX/QFX")
    
    for line in text_content.splitlines():
        line = line.strip()
        if not line:
            continue
            
        # Handle both XML-style and pure colon format transaction markers
        if line == '<STMTTRN>' or line == 'STMTTRN':
            if in_transaction and current_transaction:
                # Process the previous transaction
                try:
                    transaction = create_transaction_from_ofx(transaction_file, current_transaction, balance, import_order)
                    if transaction:
                        transactions.append(transaction)
                        balance += transaction.amount
                        import_order += 1
                except Exception as e:
                    logger.error(f"Error processing transaction: {str(e)}")
            current_transaction = {}
            in_transaction = True
        elif line == '</STMTTRN>' or (in_transaction and line.startswith('STMTTRN') and line != 'STMTTRN'):
            if in_transaction and current_transaction:
                try:
                    transaction = create_transaction_from_ofx(transaction_file, current_transaction, balance, import_order)
                    if transaction:
                        transactions.append(transaction)
                        balance += transaction.amount
                        import_order += 1
                except Exception as e:
                    logger.error(f"Error processing transaction: {str(e)}")
            current_transaction = {}
            in_transaction = False
        elif in_transaction and '>' in line and '</' in line:
            # XML-style tag with value
            tag = line[1:line.index('>')]
            value = line[line.index('>')+1:line.rindex('<')]
            current_transaction[tag] = value
        elif in_transaction and ':' in line:
            # Colon-separated style
            key, value = line.split(':', 1)
            current_transaction[key] = value.strip()
    
    # Process any remaining transaction
    if in_transaction and current_transaction:
        try:
            transaction = create_transaction_from_ofx(transaction_file, current_transaction, balance, import_order)
            if transaction:
                transactions.append(transaction)
        except Exception as e:
            logger.error(f"Error processing final transaction: {str(e)}")
    
    logger.info(f"Found {len(transactions)} transactions")
    return transactions

def create_transaction_from_ofx(transaction_file: TransactionFile, data: Dict[str, str], balance: Money, import_order: int) -> Transaction:
    """Create a transaction dictionary from OFX data."""
    try:
        # Get required fields
        date_str = data.get('DTPOSTED', '')[:8]  # Take first 8 chars for YYYYMMDD
        date_ms = parse_date(date_str)
        if not date_ms:
            logger.warning(f"Invalid date format: {date_str}")
            raise ValueError(f"Invalid date format: {date_str}")
            
        # Get amount
        amount_str = data.get('TRNAMT', '0').replace(',', '')
        if data.get('CURRENCY') != balance.currency:
            raise ValueError(f"Currency mismatch: {data.get('CURRENCY')} != {balance.currency}")
        amount = Money(Decimal(amount_str), balance.currency)
        
        # Get description from n tag, NAME, or MEMO
        description = data.get('n') or data.get('NAME') or data.get('MEMO', '')
        
        if not transaction_file.account_id:
            raise ValueError("Account ID is required")
        if not transaction_file.user_id:
            raise ValueError("User ID is required")
        if not transaction_file.file_id:
            raise ValueError("File ID is required")
        # Create transaction
        transaction = Transaction.create(
            account_id=transaction_file.account_id,
            user_id=transaction_file.user_id,
            file_id=transaction_file.file_id,
            date=date_ms,
            description=description.strip(),
            amount=amount,
            balance=balance + amount,
            import_order=import_order,
            transaction_type=data.get('TRNTYPE', '').strip().upper() if data.get('TRNTYPE') else None
        )
        
            
        return transaction
    except Exception as e:
        raise ValueError(f"Error creating transaction: {str(e)}")

def parse_ofx_transactions(transaction_file: TransactionFile, content: bytes) -> List[Transaction]:
    """Parse transactions from OFX/QFX file content."""
    try:
        # Decode the content
        text_content = content.decode('utf-8')
        logger.info("Parsing OFX/QFX content")
        
        # Check if this is a colon-separated format
        if any(marker in text_content for marker in ['OFXHEADER:', 'DATA:OFXSGML', 'STMTTRN']):
            logger.info("Detected colon-separated OFX/QFX format")
            return parse_ofx_colon_separated(text_content, transaction_file)
            
        # Try parsing as XML
        try:
            logger.info("Attempting to parse as XML")
            root = ET.fromstring(text_content)
            transactions = []
            if not transaction_file.opening_balance:
                raise ValueError("Opening balance is required")
            balance: Money = transaction_file.opening_balance
            
            # Find all transaction elements
            for i, stmttrn in enumerate(root.findall('.//STMTTRN'), 1):
                try:
                    # Extract transaction data
                    data = {
                        'DTPOSTED': stmttrn.findtext('DTPOSTED', ''),
                        'TRNAMT': stmttrn.findtext('TRNAMT', '0'),
                        'n': stmttrn.findtext('n'),
                        'NAME': stmttrn.findtext('NAME'),
                        'MEMO': stmttrn.findtext('MEMO'),
                        'TRNTYPE': stmttrn.findtext('TRNTYPE'),
                        'CURRENCY': stmttrn.findtext('CURRENCY')
                    }
                    
                    transaction = create_transaction_from_ofx(transaction_file, data, balance, i)
                    if transaction:
                        transactions.append(transaction)
                        balance += transaction.amount
                        
                except Exception as e:
                    logger.error(f"Error processing XML transaction: {str(e)}")
                    continue
                    
            logger.info(f"Found {len(transactions)} transactions in XML format")
            return transactions
            
        except ET.ParseError:
            logger.error("Failed to parse as XML")
            return []
            
    except Exception as e:
        logger.error(f"Error parsing OFX/QFX content: {str(e)}")
        return []

def file_type_selector(content: bytes) -> Optional[FileFormat]:
    """
    Detect the file format (CSV, OFX, QFX) from the raw content bytes.
    Returns a FileFormat enum value if positively determined, otherwise None.
    """
    try:
        text = content.decode('utf-8', errors='ignore').strip()
    except Exception:
        return None  # Could not decode

    # Check for OFX/QFX markers
    if text.startswith('<OFX') or 'OFXHEADER:' in text or 'DATA:OFXSGML' in text:
        return FileFormat.OFX
    if text.startswith('<QFX'):
        return FileFormat.QFX
    # Check for XML root tag
    if text.startswith('<?xml') or text.startswith('<'):
        # Heuristic: if it contains <OFX> or <QFX> tags, treat as OFX/QFX
        if '<OFX>' in text or '<OFX ' in text:
            return FileFormat.OFX
        if '<QFX>' in text or '<QFX ' in text:
            return FileFormat.QFX
    # Heuristic for CSV: must have at least one comma in the first line and no XML/OFX/QFX markers
    first_line = text.splitlines()[0] if text else ''
    if ',' in first_line and not any(marker in text for marker in ['<OFX', '<QFX', 'OFXHEADER:', 'DATA:OFXSGML', '<?xml']):
        return FileFormat.CSV
    # Could not positively determine
    return FileFormat.OTHER