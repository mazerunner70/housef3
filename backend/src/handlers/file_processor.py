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

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for processing S3 upload events.
    
    Args:
        event: S3 event data
        context: Lambda context
        
    Returns:
        Response object
    """
    logger.info(f"Processing S3 event: {json.dumps(event)}")
    
    # Process each record in the S3 event
    for record in event.get('Records', []):
        try:
            # Extract S3 bucket and key
            s3_event = record.get('s3', {})
            bucket_name = s3_event.get('bucket', {}).get('name')
            object_key = urllib.parse.unquote_plus(s3_event.get('object', {}).get('key'))
            
            if not bucket_name or not object_key:
                logger.error("Missing bucket name or object key in S3 event")
                continue
                
            logger.info(f"Processing file: {object_key} in bucket: {bucket_name}")
            
            # Find the file record in DynamoDB that matches the S3 key
            file_records = find_file_records_by_s3_key(object_key)
            
            if not file_records:
                logger.warning(f"No file record found for S3 key: {object_key}")
                continue
                
            # There should typically be only one record, but process all matches just in case
            for file_record in file_records:
                file_id = file_record.get('fileId')
                logger.info(f"Found file record with ID: {file_id}")
                
                # Update processing status to "processing"
                update_transaction_file(file_id, {
                    'processingStatus': ProcessingStatus.PROCESSING.value
                })
                
                try:
                    # Get the file content
                    response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
                    content_bytes = response['Body'].read()
                    
                    # Analyze the file format
                    detected_format = analyze_file_format(bucket_name, object_key)
                    logger.info(f"Detected file format: {detected_format} for file: {file_id}")
                    
                    # Try to extract opening balance from financial files
                    opening_balance = None
                    if detected_format in [FileFormat.OFX, FileFormat.QFX, FileFormat.CSV]:
                        opening_balance = extract_opening_balance(content_bytes, detected_format)
                        if opening_balance is not None:
                            logger.info(f"Extracted opening balance: {opening_balance}")
                    
                    # Compare with the format in the record
                    current_format = FileFormat(file_record.get('fileFormat', 'other'))
                    
                    # Prepare update data
                    update_data = {
                        'processingStatus': ProcessingStatus.PROCESSED.value
                    }
                    
                    if current_format != detected_format:
                        logger.info(f"Updating file format from {current_format} to {detected_format}")
                        update_data['fileFormat'] = detected_format.value
                    
                    if opening_balance is not None:
                        update_data['openingBalance'] = str(opening_balance)
                    
                    # Update the file record
                    update_transaction_file(file_id, update_data)
                        
                except Exception as analysis_error:
                    logger.error(f"Error analyzing file {file_id}: {str(analysis_error)}")
                    update_transaction_file(file_id, {
                        'processingStatus': ProcessingStatus.ERROR.value,
                        'errorMessage': f"Error analyzing file format: {str(analysis_error)}"
                    })
                    
        except Exception as e:
            logger.error(f"Error processing S3 event record: {str(e)}")
    
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "File processing completed"})
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
        s3_key: S3 object key to match
        
    Returns:
        List of matching file records
    """
    try:
        # Query for records with the matching S3 key
        response = file_table.scan(
            FilterExpression="s3Key = :key",
            ExpressionAttributeValues={
                ":key": s3_key
            }
        )
        
        return response.get('Items', [])
    except Exception as e:
        logger.error(f"Error querying for file records by S3 key: {str(e)}")
        return [] 