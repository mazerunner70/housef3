"""
S3 Event Handler for File Uploads

This Lambda handler is triggered by S3 ObjectCreated events and publishes
FileUploadedEvent to EventBridge instead of processing files directly.
This enables event-driven file processing through the consumer architecture.
"""
import json
import logging
import os
import sys
import traceback
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Fix imports for Lambda environment
try:
    if '/var/task' not in sys.path:
        sys.path.insert(0, '/var/task')
    
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
        
    logger.info("Successfully adjusted Python path for Lambda environment")
except Exception as e:
    logger.error(f"Import path setup error: {str(e)}")
    raise

# Import after path fixing
from services.event_service import event_service
from models.events import FileUploadedEvent
from utils.s3_dao import get_object_metadata

# Event publishing configuration
ENABLE_EVENT_PUBLISHING = os.environ.get('ENABLE_EVENT_PUBLISHING', 'true').lower() == 'true'


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle S3 ObjectCreated events by publishing FileUploadedEvent to EventBridge.
    
    This handler replaces direct file processing and enables event-driven architecture.
    
    Args:
        event: S3 event notification
        context: Lambda context
        
    Returns:
        Dict containing processing results
    """
    try:
        logger.info(f"S3 event handler received event: {json.dumps(event)}")
        
        # Process each S3 record
        processed_count = 0
        failed_count = 0
        
        for record in event.get('Records', []):
            try:
                # Extract S3 event information
                event_name = record.get('eventName', '')
                if not event_name.startswith('ObjectCreated'):
                    logger.info(f"Skipping non-create event: {event_name}")
                    continue
                
                bucket = record.get('s3', {}).get('bucket', {}).get('name')
                key = record.get('s3', {}).get('object', {}).get('key')
                size = record.get('s3', {}).get('object', {}).get('size', 0)
                
                if not bucket or not key:
                    logger.warning("Missing bucket or key in S3 record; skipping")
                    failed_count += 1
                    continue
                
                # Skip restore packages - they have their own consumer
                if key.startswith('restore_packages/'):
                    logger.info(f"Skipping restore package: {key}")
                    continue
                
                # Extract user ID and filename from key (format: userId/fileId/filename)
                key_parts = key.split('/')
                if len(key_parts) != 3:
                    logger.warning(f"Invalid S3 key format: {key}")
                    failed_count += 1
                    continue
                    
                user_id = key_parts[0]
                file_name = key_parts[2]
                
                # Get file metadata from S3
                metadata = get_object_metadata(key, bucket)
                if metadata is None:
                    logger.error(f"Could not get metadata for file: {key}")
                    failed_count += 1
                    continue
                
                file_id = metadata.get('metadata', {}).get('fileid')
                if not file_id:
                    logger.error(f"File ID not found in S3 metadata for: {key}")
                    failed_count += 1
                    continue
                
                account_id = metadata.get('metadata', {}).get('accountid')
                
                logger.info(f"Processing S3 upload event - User: {user_id}, File ID: {file_id}, "
                           f"S3 Key: {key}, Name: {file_name}, Size: {size}")
                
                # Publish FileUploadedEvent if event publishing is enabled
                if ENABLE_EVENT_PUBLISHING:
                    try:
                        file_uploaded_event = FileUploadedEvent(
                            user_id=user_id,
                            file_id=file_id,
                            file_name=file_name,
                            file_size=size,
                            s3_key=key,
                            account_id=account_id
                        )
                        
                        event_service.publish_event(file_uploaded_event)
                        logger.info(f"FileUploadedEvent published for file {file_id}")
                        processed_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to publish FileUploadedEvent for file {file_id}: {str(e)}")
                        failed_count += 1
                        continue
                else:
                    logger.info(f"Event publishing disabled, skipping FileUploadedEvent for file {file_id}")
                    processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing S3 record: {str(e)}")
                logger.error(f"Record: {json.dumps(record)}")
                logger.error(f"Stack trace: {traceback.format_exc()}")
                failed_count += 1
                continue
        
        # Return processing summary
        total_records = len(event.get('Records', []))
        logger.info(f"S3 event processing complete: {processed_count}/{total_records} processed, "
                   f"{failed_count} failed")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Processed {processed_count} file upload events',
                'processed': processed_count,
                'failed': failed_count,
                'total': total_records
            })
        }
        
    except Exception as e:
        logger.error(f"Critical error in S3 event handler: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f"Critical error in S3 event handler: {str(e)}"
            })
        }
