"""
Lambda handler for processing uploaded files in S3 and analyzing their format.
This function is triggered by S3 ObjectCreated events.
"""
import json
import logging
import os
import urllib.parse
import boto3
from typing import Dict, Any, List

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

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
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
                
                # Analyze the file format
                try:
                    detected_format = analyze_file_format(bucket_name, object_key)
                    logger.info(f"Detected file format: {detected_format} for file: {file_id}")
                    
                    # Compare with the format in the record
                    current_format = FileFormat(file_record.get('fileFormat', 'other'))
                    
                    if current_format != detected_format:
                        logger.info(f"Updating file format from {current_format} to {detected_format}")
                        
                        # Update the file record with the correct format
                        update_transaction_file(file_id, {
                            'fileFormat': detected_format.value,
                            'processingStatus': ProcessingStatus.PROCESSED.value
                        })
                    else:
                        # Format was already correct, just update status
                        update_transaction_file(file_id, {
                            'processingStatus': ProcessingStatus.PROCESSED.value
                        })
                        
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