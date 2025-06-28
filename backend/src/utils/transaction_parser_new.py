"""
Functional Transaction Parser - Redesigned with Dataclass + Functional Approach

This module implements a clean, functional approach to transaction parsing while
preserving critical business logic from the original parser.

🔒 PROTECTED FUNCTIONS are preserved exactly as-is to maintain compatibility
with real-world CSV files and existing field mapping logic.
"""

import csv
import io
import logging
import logging.config
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

# Model imports
from models.account import Currency
from models.transaction import Transaction
from models.transaction_file import FileFormat, TransactionFile
from models.file_map import FileMap
from utils.db_utils import checked_mandatory_file_map

def parse_ofx_headers(content: bytes) -> Dict[str, str]:
    """
    Parse OFX headers to extract encoding and other metadata.
    
    Args:
        content: Raw bytes content of the OFX file
        
    Returns:
        Dictionary of header key-value pairs
    """
    headers = {}
    
    # Try to decode with common encodings to read headers
    for encoding in ['ascii', 'utf-8', 'latin-1', 'cp1252']:
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        # If all encodings fail, use utf-8 with error handling
        text = content.decode('utf-8', errors='ignore')
    logger.info(f"Decoded OFX content using encoding: {text}")
    lines = text.splitlines()
    
    # Parse header lines (before <OFX> tag)
    for line in lines:
        line = line.strip()
        if line.startswith('<'):
            break  # End of headers
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
    
    logger.debug(f"Parsed OFX headers: {headers}")
    return headers

def get_ofx_encoding(headers: Dict[str, str]) -> str:
    """
    Determine the correct encoding from OFX headers.
    
    Args:
        headers: Dictionary of parsed OFX headers
        
    Returns:
        Encoding string to use for decoding
    """
    # Check CHARSET header first
    charset = headers.get('CHARSET', '').upper()
    encoding_header = headers.get('ENCODING', '').upper()
    
    # Map common OFX charset values to Python encodings
    charset_map = {
        '1252': 'cp1252',        # Windows-1252
        'WINDOWS-1252': 'cp1252',
        'CP1252': 'cp1252',
        'ISO-8859-1': 'latin-1',
        'UTF-8': 'utf-8',
        'ASCII': 'ascii',
        'USASCII': 'ascii'
    }
    
    # First try charset mapping
    if charset in charset_map:
        encoding = charset_map[charset]
        logger.info(f"Using encoding '{encoding}' from CHARSET header: {charset}")
        return encoding
    
    # Then try encoding header
    if encoding_header in charset_map:
        encoding = charset_map[encoding_header]
        logger.info(f"Using encoding '{encoding}' from ENCODING header: {encoding_header}")
        return encoding
    
    # Default fallback
    logger.warning(f"Unknown charset/encoding in headers. CHARSET: {charset}, ENCODING: {encoding_header}. Defaulting to cp1252")
    return 'cp1252'

# Configure logging
log_conf = os.environ.get('LOGGING_CONFIG')
if log_conf:
    logging.config.fileConfig(log_conf)
else:
    logging.basicConfig(
        level=os.environ.get('LOG_LEVEL', 'INFO'),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# =============================================================================
# 🔒 PROTECTED FUNCTIONS - PRESERVED EXACTLY AS-IS
# These functions handle critical business logic and must not be modified
# =============================================================================

def preprocess_csv_text(text_content: str) -> str:
    """
    🔒 PROTECTED: Critical business logic for real-world CSV parsing
    
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
            
        # Parse the line, applying strip to every parsed field
        fields = [field.strip() for field in parse_csv_line(line)]
        
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


def apply_field_mapping(row_data: Dict[str, Any], field_map: FileMap) -> Dict[str, Any]:
    """
    🔒 PROTECTED: Core field mapping logic - must preserve exact behavior
    
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
                # Use a safer approach instead of eval()
                value = _apply_safe_transformation(mapping.transformation, value)
                logger.info(f"Transformed value: {value}")
            except Exception as e:
                logger.error(f"Error applying transformation {mapping.transformation}: {str(e)}")
                continue
        
        result[target] = value
    
    logger.info(f"Final mapped result: {result}")
    return result


def _apply_safe_transformation(transformation: str, value: Any) -> Any:
    """
    Apply transformation safely without using eval().
    
    Args:
        transformation: The transformation string
        value: The input value
        
    Returns:
        Transformed value
    """
    # For now, support basic transformations
    # This could be expanded to use a proper expression parser like simpleeval
    if transformation == "value.strip()":
        return str(value).strip()
    elif transformation == "value.upper()":
        return str(value).upper()
    elif transformation == "value.lower()":
        return str(value).lower()
    elif transformation.startswith("-"):
        # Handle negation: "-value"
        if transformation == "-value":
            return -float(value)
    
    # For complex transformations, consider using a library like simpleeval
    # For now, log and return unchanged
    logger.warning(f"Unsupported transformation: {transformation}, returning value unchanged")
    return value


def detect_date_order(dates: List[str]) -> str:
    """
    🔒 PROTECTED: Critical for maintaining correct running balances
    
    Detect if dates are in ascending or descending order.
    """
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


# =============================================================================
# NEW FUNCTIONAL DESIGN - DATACLASSES AND PURE FUNCTIONS
# =============================================================================

@dataclass
class ParsedTransactionData:
    """Clean data structure for parsed transaction information"""
    date: int
    description: str
    amount: Decimal
    currency: Optional[Currency] = None
    balance: Optional[Decimal] = None
    memo: Optional[str] = None
    transaction_type: Optional[str] = None
    check_number: Optional[str] = None
    fit_id: Optional[str] = None
    status: Optional[str] = None


@dataclass
class ParsingContext:
    """Context object for passing parsing parameters - pythonic approach"""
    transaction_file: TransactionFile
    file_map: FileMap
    current_balance: Decimal = field(default_factory=lambda: Decimal(0))
    import_order: int = 1


# =============================================================================
# IMPROVED DATE PROCESSING - ANALYZE ALL DATES TO DETERMINE FORMAT
# =============================================================================

def determine_date_format(date_strings: List[str], format_type: str = 'csv') -> Optional[str]:
    """
    Analyze all date strings in the file to determine the correct date format.
    
    This is much more robust than trying formats individually, as it:
    1. Ensures consistency across the entire file
    2. Is more efficient (determine format once)
    3. Provides better error detection
    
    Args:
        date_strings: List of all date strings from the file
        format_type: Type of file format ('csv', 'ofx', 'qif')
    
    Returns:
        The date format string that works for all dates, or None if no format works
    """
    # Define format sets by file type
    format_sets = {
        'csv': [
            "%Y-%m-%d",     # 2024-01-15
            "%m/%d/%Y",     # 1/15/2024 (US format)
            "%d/%m/%Y",     # 15/1/2024 (EU format)
            "%Y%m%d",       # 20240115
            "%m-%d-%Y",     # 1-15-2024
            "%d-%m-%Y",     # 15-1-2024
            "%m/%d/%y",     # 1/15/24
            "%d/%m/%y",     # 15/1/24
        ],
        'ofx': [
            "%Y%m%d",       # 20240115 (standard OFX)
        ],
        'qif': [
            "%d/%m/%Y",     # 15/01/2024
            "%d/%m/%y",     # 15/01/24
            "%m/%d/%Y",     # 1/15/2024
            "%m/%d/%y",     # 1/15/24  
            "%m/%d'%y",     # 1/15'24 (Quicken format)
            "%m/ %d/%y",    # 1/ 1/24 (spaces)
            "%Y-%m-%d"      # 2024-01-15
        ]
    }
    
    formats_to_try = format_sets.get(format_type, format_sets['csv'])
    
    # Filter out empty or None date strings
    valid_dates = [d.strip() for d in date_strings if d and d.strip()]
    
    if not valid_dates:
        logger.warning("No valid date strings provided")
        return None
    
    logger.info(f"Analyzing {len(valid_dates)} date strings to determine format")
    logger.debug(f"Sample dates: {valid_dates[:5]}")  # Log first 5 dates for debugging
    
    # Try each format and count successful parses
    best_format = None
    best_success_rate = 0
    
    for fmt in formats_to_try:
        successful_parses = 0
        total_attempts = 0
        
        for date_str in valid_dates:
            total_attempts += 1
            try:
                # For OFX dates, handle timestamp format (take first 8 chars)
                test_date = date_str
                if format_type == 'ofx' and len(test_date) > 8:
                    test_date = test_date[:8]
                
                datetime.strptime(test_date, fmt)
                successful_parses += 1
            except ValueError:
                continue
        
        success_rate = successful_parses / total_attempts if total_attempts > 0 else 0
        
        logger.debug(f"Format '{fmt}': {successful_parses}/{total_attempts} successful ({success_rate:.2%})")
        
        # A format must work for at least 90% of dates to be considered valid
        # This allows for some malformed dates while ensuring consistency
        if success_rate >= 0.9 and success_rate > best_success_rate:
            best_format = fmt
            best_success_rate = success_rate
            
        # If we find a format that works for 100% of dates, use it immediately
        if success_rate == 1.0:
            logger.info(f"Found perfect date format: '{fmt}' (100% success)")
            return fmt
    
    if best_format and best_success_rate >= 0.9:
        logger.info(f"Determined date format: '{best_format}' ({best_success_rate:.2%} success)")
        return best_format
    else:
        logger.error(f"Could not determine date format. Best was '{best_format}' with {best_success_rate:.2%} success")
        return None


def parse_date_with_format(date_str: str, date_format: str, format_type: str = 'csv') -> int:
    """
    Parse a single date string using a predetermined format.
    
    Args:
        date_str: The date string to parse
        date_format: The date format to use (determined by determine_date_format)
        format_type: Type of file format for special handling
    
    Returns:
        Milliseconds since epoch
    """
    try:
        # Handle special cases for different format types
        processed_date = date_str.strip()
        
        if format_type == 'ofx' and len(processed_date) > 8:
            processed_date = processed_date[:8]  # Take first 8 chars for YYYYMMDD
        
        dt = datetime.strptime(processed_date, date_format)
        return int(dt.timestamp() * 1000)
        
    except ValueError as e:
        raise ValueError(f"Failed to parse date '{date_str}' with format '{date_format}': {str(e)}")


# =============================================================================
# FORMAT-SPECIFIC DATE PARSING FUNCTIONS (SIMPLIFIED)
# =============================================================================

def parse_csv_date(date_str: str, date_format: str) -> int:
    """Parse CSV date using predetermined format"""
    return parse_date_with_format(date_str, date_format, 'csv')


def parse_ofx_date(date_str: str, date_format: str) -> int:
    """Parse OFX date using predetermined format"""
    return parse_date_with_format(date_str, date_format, 'ofx')


def parse_qif_date(date_str: str, date_format: str) -> int:
    """Parse QIF date using predetermined format"""
    return parse_date_with_format(date_str, date_format, 'qif')


# =============================================================================
# FORMAT-SPECIFIC AMOUNT PROCESSING FUNCTIONS
# =============================================================================

def process_csv_amount(amount_str: str, debit_credit: Optional[str] = None) -> Decimal:
    """Process CSV amount with optional debit/credit indicator"""
    amount = Decimal(str(amount_str).replace(',', ''))
    if debit_credit and debit_credit.upper() == 'DBIT':
        return -abs(amount)
    return amount


def process_ofx_amount(amount_str: str) -> Decimal:
    """Process OFX amount (already signed)"""
    return Decimal(str(amount_str).replace(',', ''))


def process_qif_amount(amount_str: str) -> Decimal:
    """Process QIF amount (negate for consistency)"""
    return -Decimal(str(amount_str).replace(',', ''))


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def find_column_index(header: List[str], possible_names: List[str]) -> Optional[int]:
    """Find the index of a column given possible column names"""
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


def validate_transaction_file(transaction_file: TransactionFile) -> None:
    """Validate required transaction file fields"""
    if not transaction_file.account_id:
        raise ValueError("Account ID is required")
    if not transaction_file.user_id:
        raise ValueError("User ID is required")
    if not transaction_file.file_id:
        raise ValueError("File ID is required")
    if not transaction_file.file_map_id:
        raise ValueError("File map ID is required")


def create_transaction_from_parsed_data(
    parsed_data: ParsedTransactionData,
    context: ParsingContext
) -> Transaction:
    """Create a Transaction object from parsed data and context"""
    # Validate required IDs
    if not context.transaction_file.account_id:
        raise ValueError("Account ID is required")
    if not context.transaction_file.user_id:
        raise ValueError("User ID is required")
    if not context.transaction_file.file_id:
        raise ValueError("File ID is required")
    
    # Update balance
    new_balance = context.current_balance + parsed_data.amount
    
    transaction = Transaction.create(
        account_id=context.transaction_file.account_id,
        user_id=context.transaction_file.user_id,
        file_id=context.transaction_file.file_id,
        date=parsed_data.date,
        description=parsed_data.description.strip(),
        amount=parsed_data.amount,
        currency=parsed_data.currency or context.transaction_file.currency,
        balance=new_balance,
        import_order=context.import_order,
        transaction_type=parsed_data.transaction_type,
        memo=parsed_data.memo,
        check_number=parsed_data.check_number,
        fit_id=parsed_data.fit_id,
        status=parsed_data.status
    )
    
    # Update context for next transaction
    context.current_balance = new_balance
    context.import_order += 1
    
    return transaction


# =============================================================================
# ORCHESTRATOR PATTERN - MODULAR ARCHITECTURE
# =============================================================================

@dataclass
class DateInfo:
    """Information about date processing for the file"""
    format_string: str
    order: str  # 'asc' or 'desc'
    sample_dates: List[str]


def extract_raw_transactions(transaction_file: TransactionFile, content: bytes) -> List[Dict[str, str]]:
    """Dispatch to format-specific extractor"""
    if not transaction_file.file_format:
        raise ValueError("File format is required")
    
    extractors = {
        FileFormat.CSV: extract_raw_transactions_csv,
        FileFormat.OFX: extract_raw_transactions_ofx,
        FileFormat.QFX: extract_raw_transactions_ofx,  # QFX uses same extractor as OFX
        FileFormat.QIF: extract_raw_transactions_qif,
    }
    extractor = extractors.get(transaction_file.file_format)
    if not extractor:
        raise ValueError(f"No extractor for format: {transaction_file.file_format}")
    
    return extractor(transaction_file, content)


def extract_raw_transactions_csv(transaction_file: TransactionFile, content: bytes) -> List[Dict[str, str]]:
    """
    Extract raw CSV data into list of dictionaries.
    🔒 CRITICAL: Uses protected preprocess_csv_text() function
    """
    raw_content = content.decode('utf-8')
    preprocessed_content = preprocess_csv_text(raw_content)  # 🔒 PROTECTED
    
    if len(preprocessed_content.splitlines()) != len(raw_content.splitlines()):
        raise ValueError("Preprocessing CSV text resulted in a different number of lines")
    
    # Create custom CSV dialect
    class QuotedDialect(csv.Dialect):
        delimiter = ','
        quotechar = '"'
        doublequote = True
        skipinitialspace = True
        lineterminator = '\n'
        quoting = csv.QUOTE_MINIMAL
    
    # Parse CSV into raw dictionaries
    csv_file = io.StringIO(preprocessed_content)
    reader = csv.DictReader(csv_file, dialect=QuotedDialect())
    
    return [dict(row) for row in reader]


def extract_raw_transactions_ofx(transaction_file: TransactionFile, content: bytes) -> List[Dict[str, str]]:
    """Extract raw OFX data into list of dictionaries"""
    # Parse OFX headers to get correct encoding
    headers = parse_ofx_headers(content)
    encoding = get_ofx_encoding(headers)
    
    # Decode the content using the correct encoding
    try:
        text_content = content.decode(encoding)
        logger.info(f"Successfully decoded OFX content using encoding: {encoding}")
    except UnicodeDecodeError as e:
        logger.warning(f"Failed to decode with {encoding}, falling back to utf-8: {str(e)}")
        text_content = content.decode('utf-8', errors='replace')
    
    # Try to determine OFX format - don't assume XML!
    # Check if it contains XML-like or colon-separated transaction data
    has_xml_like_tags = '<STMTTRN>' in text_content or '<TRNTYPE>' in text_content or '<DTPOSTED>' in text_content
    has_colon_format = any(':' in line and not line.startswith('<') for line in text_content.splitlines() if line.strip())
    
    if has_xml_like_tags:
        # This could be OFX SGML (XML-like) or true XML
        try:
            # First try as true XML
            return _extract_ofx_xml(text_content)
        except ET.ParseError:
            # If XML parsing fails, treat as OFX SGML (XML-like but not valid XML)
            logger.info("XML parsing failed, treating as OFX SGML format")
            return _extract_ofx_colon_separated(text_content)
    elif has_colon_format:
        # Pure colon-separated format
        return _extract_ofx_colon_separated(text_content)
    else:
        # Fallback - try both approaches
        logger.warning("Could not determine OFX format, trying colon-separated first")
        result = _extract_ofx_colon_separated(text_content)
        if not result:
            try:
                return _extract_ofx_xml(text_content)
            except ET.ParseError:
                logger.error("Both OFX parsing methods failed")
                return []
        return result


def extract_raw_transactions_qif(transaction_file: TransactionFile, content: bytes) -> List[Dict[str, str]]:
    """Extract raw QIF data into list of dictionaries"""
    text_content = content.decode('utf-8')
    transactions = []
    current_transaction = {}
    
    for line in text_content.splitlines():
        line = line.strip()
        if line == '^':  # End of transaction
            if current_transaction:
                transactions.append(current_transaction.copy())
            current_transaction = {}
        elif len(line) >= 2:
            field_code = line[0]
            field_value = line[1:]
            current_transaction[field_code] = field_value
    
    # Add final transaction if exists
    if current_transaction:
        transactions.append(current_transaction)
    
    return transactions


def apply_mappings_to_transactions(raw_transactions: List[Dict[str, str]], transaction_file: TransactionFile) -> List[Dict[str, Any]]:
    """
    Apply field mappings to all transactions.
    🔒 CRITICAL: Uses protected apply_field_mapping() function
    """
    file_map = checked_mandatory_file_map(transaction_file.file_map_id, transaction_file.user_id)
    mapped_transactions = []
    
    for raw_txn in raw_transactions:
        # 🔒 PROTECTED: Use existing field mapping function
        mapped_data = apply_field_mapping(raw_txn, file_map)
        if mapped_data:
            mapped_transactions.append(mapped_data)
    
    return mapped_transactions


def determine_dates_and_order(mapped_transactions: List[Dict[str, Any]], file_format: Optional[FileFormat]) -> DateInfo:
    """
    Determine date format and order from mapped transaction data.
    Combines collective date analysis with order detection.
    """
    if not file_format:
        raise ValueError("File format is required")
    
    # Extract date strings from mapped 'date' field (field mapping already applied)
    date_strings = [txn.get('date', '') for txn in mapped_transactions if txn.get('date', '').strip()]
    
    # Determine format using collective analysis
    format_type_map = {
        FileFormat.CSV: 'csv',
        FileFormat.OFX: 'ofx', 
        FileFormat.QFX: 'ofx',
        FileFormat.QIF: 'qif'
    }
    
    date_format = determine_date_format(date_strings, format_type_map[file_format])
    if not date_format:
        raise ValueError(f"Could not determine date format for {file_format} file")
    
    # 🔒 PROTECTED: Use existing date order detection
    order = detect_date_order(date_strings)
    
    return DateInfo(
        format_string=date_format,
        order=order,
        sample_dates=date_strings[:5]  # Keep samples for logging
    )


def create_transactions_from_mapped_data(
    mapped_transactions: List[Dict[str, Any]], 
    transaction_file: TransactionFile,
    date_info: DateInfo
) -> List[Transaction]:
    """
    Create Transaction objects from mapped data.
    Universal function that works for all formats.
    """
    if not transaction_file.file_format:
        raise ValueError("File format is required")
    
    file_map = checked_mandatory_file_map(transaction_file.file_map_id, transaction_file.user_id)
    context = ParsingContext(
        transaction_file=transaction_file,
        file_map=file_map,
        current_balance=transaction_file.opening_balance or Decimal(0),
        import_order=1
    )
    
    transactions = []
    
    # Sort by date if needed
    if date_info.order == 'asc':
        mapped_transactions.reverse()
    
    for mapped_data in mapped_transactions:
        try:
            # Parse using determined date format
            format_type = {
                FileFormat.CSV: 'csv',
                FileFormat.OFX: 'ofx',
                FileFormat.QFX: 'ofx', 
                FileFormat.QIF: 'qif'
            }[transaction_file.file_format]
            
            # Determine if amounts should be reversed based on file mapping
            reverse_amounts = file_map.reverse_amounts if file_map else False
            
            parsed_data = ParsedTransactionData(
                date=parse_date_with_format(mapped_data['date'], date_info.format_string, format_type),
                description=mapped_data.get('description', ''),
                amount=_process_amount_for_format(mapped_data, transaction_file.file_format, reverse_amounts),
                currency=_parse_currency(mapped_data.get('currency')) or transaction_file.currency,
                memo=mapped_data.get('memo'),
                transaction_type=mapped_data.get('debitOrCredit') or mapped_data.get('transactionType'),
                check_number=mapped_data.get('checkNumber'),
                fit_id=mapped_data.get('fitId'),
                status=mapped_data.get('status')
            )
            
            transaction = create_transaction_from_parsed_data(parsed_data, context)
            transactions.append(transaction)
            
        except Exception as e:
            logger.error(f"Error creating transaction from mapped data: {str(e)}")
            continue
    
    return transactions


def parse_transactions_orchestrator(transaction_file: TransactionFile, content: bytes) -> Optional[List[Transaction]]:
    """
    Universal transaction parser orchestrator.
    Uses format-specific extractors but common processing pipeline.
    """
    try:
        # Step 1: Extract raw transaction data (format-specific)
        raw_transactions = extract_raw_transactions(transaction_file, content)
        # get first 500 chars of raw_transactions
        # Step 2: Apply field mappings (🔒 PROTECTED - universal)
        mapped_transactions = apply_mappings_to_transactions(raw_transactions, transaction_file)
        
        # Step 3: Analyze dates and determine order (now that we know the date field)
        date_info = determine_dates_and_order(mapped_transactions, transaction_file.file_format)
        
        # Step 4: Create transaction objects (universal)
        return create_transactions_from_mapped_data(mapped_transactions, transaction_file, date_info)
        
    except Exception as e:
        logger.error(f"Error in transaction parsing orchestrator: {str(e)}")
        return []


# =============================================================================
# HELPER FUNCTIONS FOR UNIVERSAL PROCESSING
# =============================================================================

def _process_amount_for_format(mapped_data: Dict[str, Any], file_format: Optional[FileFormat], reverse_amounts: bool = False) -> Decimal:
    """Process amount based on file format"""
    if not file_format:
        raise ValueError("File format is required")
    
    amount_str = str(mapped_data.get('amount', '0'))
    
    if file_format == FileFormat.CSV:
        amount = process_csv_amount(amount_str, mapped_data.get('debitOrCredit'))
    elif file_format in [FileFormat.OFX, FileFormat.QFX]:
        amount = process_ofx_amount(amount_str)
    elif file_format == FileFormat.QIF:
        amount = process_qif_amount(amount_str)
    else:
        amount = Decimal(amount_str.replace(',', ''))
    
    # Apply reverse amounts flag if specified
    if reverse_amounts:
        amount = -amount
    
    return amount


def _parse_currency(currency_str: Optional[str]) -> Optional[Currency]:
    """Parse currency string to Currency enum"""
    if not currency_str:
        return None
    try:
        return Currency(currency_str.strip())
    except ValueError:
        logger.warning(f"Invalid currency value: {currency_str}")
        return None


def _extract_ofx_colon_separated(text_content: str) -> List[Dict[str, str]]:
    """Extract OFX data from colon-separated format"""
    transactions = []
    current_transaction = {}
    in_transaction = False
    
    for line in text_content.splitlines():
        line = line.strip()
        if not line:
            continue
            
        # Handle transaction markers
        if line == '<STMTTRN>' or line == 'STMTTRN':
            if in_transaction and current_transaction:
                transactions.append(current_transaction.copy())
            current_transaction = {}
            in_transaction = True
        elif line == '</STMTTRN>' or (in_transaction and line.startswith('STMTTRN') and line != 'STMTTRN'):
            if in_transaction and current_transaction:
                transactions.append(current_transaction.copy())
            current_transaction = {}
            in_transaction = False
        elif in_transaction and '>' in line and '</' in line:
            # XML-style tag with value on same line with closing tag
            tag = line[1:line.index('>')]
            value = line[line.index('>')+1:line.rindex('<')]
            current_transaction[tag] = value
        elif in_transaction and line.startswith('<') and '>' in line and not line.endswith('>'):
            # XML-style tag with value on same line but no closing tag
            tag = line[1:line.index('>')]
            value = line[line.index('>')+1:]
            current_transaction[tag] = value
        elif in_transaction and ':' in line:
            # Colon-separated style
            key, value = line.split(':', 1)
            current_transaction[key] = value.strip()
    
    # Process any remaining transaction
    if in_transaction and current_transaction:
        transactions.append(current_transaction)
    
    return transactions


def _extract_ofx_xml(text_content: str) -> List[Dict[str, str]]:
    """Extract OFX data from XML format"""
    try:
        # Strip OFX headers - find the start of XML content
        xml_start = -1
        lines = text_content.splitlines()
        
        for i, line in enumerate(lines):
            line = line.strip()
            # Look for XML start - either <?xml or <OFX or first < tag
            if line.startswith('<?xml') or line.startswith('<OFX') or (line.startswith('<') and not ':' in line):
                xml_start = i
                break
        
        if xml_start == -1:
            raise ET.ParseError("No XML content found after OFX headers")
        
        # Join remaining lines as XML content
        xml_content = '\n'.join(lines[xml_start:])
        
        if not xml_content.strip():
            raise ET.ParseError("Empty XML content after stripping headers")
        
        logger.info(f"Attempting to parse XML content starting from line {xml_start}")
        root = ET.fromstring(xml_content)
        transactions = []
        
        # Find all transaction elements
        for stmttrn in root.findall('.//STMTTRN'):
            data = {}
            
            # Extract all available fields from the XML element
            for child in stmttrn:
                data[child.tag] = child.text or ''
            
            # Ensure we have the common OFX fields even if empty
            common_fields = ['DTPOSTED', 'TRNAMT', 'NAME', 'MEMO', 'TRNTYPE', 'CURRENCY', 'FITID']
            for field in common_fields:
                if field not in data:
                    element = stmttrn.find(field)
                    data[field] = element.text if element is not None else ''
            
            transactions.append(data)
        
        return transactions
        
    except ET.ParseError as e:
        logger.error(f"Failed to parse OFX XML: {str(e)}")
        raise e

# =============================================================================
# FORMAT-SPECIFIC PARSERS (NOW USING ORCHESTRATOR)
# =============================================================================

def parse_csv_transactions(transaction_file: TransactionFile, content: bytes) -> Optional[List[Transaction]]:
    """Parse CSV transactions using orchestrator pattern"""
    try:
        validate_transaction_file(transaction_file)
        return parse_transactions_orchestrator(transaction_file, content)
    except Exception as e:
        logger.error(f"Error parsing CSV transactions: {str(e)}")
        return []


def parse_ofx_transactions(transaction_file: TransactionFile, content: bytes) -> Optional[List[Transaction]]:
    """Parse OFX/QFX transactions using orchestrator pattern"""
    try:
        validate_transaction_file(transaction_file)
        return parse_transactions_orchestrator(transaction_file, content)
    except Exception as e:
        logger.error(f"Error parsing OFX transactions: {str(e)}")
        return []


def parse_qif_transactions(transaction_file: TransactionFile, content: bytes) -> Optional[List[Transaction]]:
    """Parse QIF transactions using orchestrator pattern"""
    try:
        validate_transaction_file(transaction_file)
        return parse_transactions_orchestrator(transaction_file, content)
    except Exception as e:
        logger.error(f"Error parsing QIF transactions: {str(e)}")
        return []


# =============================================================================
# MAIN API - ORCHESTRATOR PATTERN
# =============================================================================

def parse_transactions(transaction_file: TransactionFile, content: bytes) -> Optional[List[Transaction]]:
    """
    Main API entry point - maintains exact same interface as original
    
    Parse transactions from file content based on the file format using
    orchestrator pattern with protected business logic.
    
    Args:
        transaction_file: TransactionFile object with metadata and format info
        content: The raw file content as bytes
        
    Returns:
        List of Transaction objects or None if parsing fails
    """
    try:
        validate_transaction_file(transaction_file)
        
        if not transaction_file.file_format:
            logger.warning("File format is required for transaction parsing")
            return None
        
        # Use orchestrator for all formats
        return parse_transactions_orchestrator(transaction_file, content)
        
    except Exception as e:
        logger.error(f"Error in main parse_transactions API: {str(e)}")
        return []


# =============================================================================
# LEGACY FORMAT-SPECIFIC PARSERS (FOR BACKWARD COMPATIBILITY)
# =============================================================================

# Simple dict-based dispatch - more pythonic than factory pattern
PARSERS: Dict[FileFormat, Callable[[TransactionFile, bytes], Optional[List[Transaction]]]] = {
    FileFormat.CSV: parse_csv_transactions,
    FileFormat.OFX: parse_ofx_transactions,
    FileFormat.QFX: parse_ofx_transactions,  # QFX uses same parser as OFX
    FileFormat.QIF: parse_qif_transactions,
}

def file_type_selector(content: bytes) -> Optional[FileFormat]:
    """
    Detect the file format (CSV, OFX, QFX, QIF) from the raw content bytes.
    Returns a FileFormat enum value if positively determined, otherwise None.
    """
    try:
        # For OFX files, try to use proper encoding from headers
        if b'OFXHEADER:' in content or b'DATA:OFXSGML' in content:
            headers = parse_ofx_headers(content)
            encoding = get_ofx_encoding(headers)
            try:
                text = content.decode(encoding).strip()
            except UnicodeDecodeError:
                logger.warning(f"Failed to decode OFX content using encoding: {encoding}, falling back to utf-8")
                text = content.decode('utf-8', errors='ignore').strip()
        else:
            text = content.decode('utf-8', errors='ignore').strip()
    except Exception:
        return None  # Could not decode

    # Check for QIF markers
    if text.startswith('!Type:') or '!Type:' in text[:100]:
        return FileFormat.QIF

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
    # Heuristic for CSV: must have at least one comma in the first line and no XML/OFX/QFX/QIF markers
    first_line = text.splitlines()[0] if text else ''
    if ',' in first_line and not any(marker in text for marker in ['<OFX', '<QFX', 'OFXHEADER:', 'DATA:OFXSGML', '<?xml', '!Type:']):
        return FileFormat.CSV
    # Could not positively determine
    return FileFormat.OTHER


# =============================================================================
# EXPORTED API
# =============================================================================

__all__ = [
    'parse_transactions',
    'parse_csv_transactions', 
    'parse_ofx_transactions',
    'parse_qif_transactions',
    'preprocess_csv_text',
    'apply_field_mapping',
    'detect_date_order',
    'ParsedTransactionData',
    'ParsingContext',
    'file_type_selector',
] 