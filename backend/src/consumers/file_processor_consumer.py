"""
File Processor Event Consumer Lambda

This Lambda function consumes FileUploadedEvent from EventBridge and processes
uploaded files to extract transactions. This replaces the direct S3-triggered
file processing with an event-driven approach.

Event Types Processed:
- file.uploaded: Process newly uploaded files and extract transactions
"""

import json
import logging
import os
import sys
import traceback
import uuid
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, date

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
from consumers.base_consumer import BaseEventConsumer
from models.events import BaseEvent, FileProcessedEvent
from models.transaction_file import FileFormat, ProcessingStatus, TransactionFile, TransactionFileCreate
from services.file_processor_service import process_file, FileProcessorResponse
from services.event_service import event_service
from utils.transaction_parser_new import file_type_selector
from utils.file_analyzer import analyze_file_format
from utils.db_utils import (
    create_transaction_file,
    get_account,
    get_account_default_file_map,
    get_file_map,
    get_transaction_file,
    create_transaction,
    delete_transactions_for_file,
)
from utils.s3_dao import get_object_content, get_object_metadata

# Event publishing configuration
ENABLE_EVENT_PUBLISHING = os.environ.get('ENABLE_EVENT_PUBLISHING', 'true').lower() == 'true'


def json_serial(obj: Any) -> str:
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


class FileProcessorEventConsumer(BaseEventConsumer):
    """Consumer for file upload events that processes files and extracts transactions"""
    
    # Event types that should trigger file processing
    FILE_PROCESSING_EVENT_TYPES = {
        'file.uploaded'  # New file uploads
    }
    
    def __init__(self):
        super().__init__("file_processor_consumer")
    
    def should_process_event(self, event: BaseEvent) -> bool:
        """Only process file upload events"""
        return event.event_type in self.FILE_PROCESSING_EVENT_TYPES
    
    def process_event(self, event: BaseEvent) -> None:
        """Process uploaded file and extract transactions"""
        try:
            event_type = event.event_type
            user_id = event.user_id
            
            logger.info(f"Processing {event_type} event {event.event_id} for file processing")
            
            # Extract file information from event data
            file_data = self._extract_file_data(event)
            if not file_data:
                raise ValueError(f"Could not extract file data from event {event.event_id}")
            
            logger.info(f"Processing file upload - User: {user_id}, File ID: {file_data['file_id']}, "
                       f"S3 Key: {file_data['s3_key']}, Name: {file_data['file_name']}")
            
            # Process the file
            result = self._process_uploaded_file(user_id, file_data)
            
            # Log processing results
            self._log_processing_metrics(event, result)
                
        except Exception as e:
            logger.error(f"Error processing file upload event {event.event_id}: {str(e)}")
            logger.error(f"Stacktrace: {traceback.format_exc()}")
            raise
    
    def _extract_file_data(self, event: BaseEvent) -> Optional[Dict[str, Any]]:
        """Extract file information from FileUploadedEvent data"""
        try:
            if event.event_type == 'file.uploaded':
                if event.data is None:
                    logger.warning("Event data is None")
                    return None
                
                return {
                    'file_id': event.data.get('fileId'),
                    'file_name': event.data.get('fileName'),
                    'file_size': event.data.get('fileSize'),
                    's3_key': event.data.get('s3Key'),
                    'account_id': event.data.get('accountId'),
                    'file_format': event.data.get('fileFormat')
                }
            
            logger.warning(f"Unknown event type for file processing: {event.event_type}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting file data from event: {str(e)}")
            return None
    
    def _process_uploaded_file(self, user_id: str, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the uploaded file and extract transactions"""
        
        result = {
            'success': False,
            'transaction_count': 0,
            'duplicate_count': 0,
            'error_message': None,
            'transaction_ids': []
        }
        
        try:
            file_id = file_data['file_id']
            file_name = file_data['file_name']
            file_size = file_data['file_size']
            s3_key = file_data['s3_key']
            account_id_str = file_data.get('account_id')
            
            # Parse account ID if provided
            parsed_account_id: Optional[uuid.UUID] = None
            if account_id_str:
                try:
                    parsed_account_id = uuid.UUID(account_id_str)
                    logger.info(f"Found and parsed account ID: {parsed_account_id}")
                except ValueError:
                    logger.warning(f"Invalid UUID format for accountId: {account_id_str}. Proceeding without this account_id.")
            
            # Download file from S3
            logger.info(f"Attempting to download file from S3: {s3_key}")
            content_bytes = get_object_content(s3_key)
            if content_bytes is None:
                raise ValueError(f"Could not download file content: {s3_key}")
                
            logger.info(f"Successfully downloaded file from S3, size: {len(content_bytes)} bytes")
            
            # Detect file type
            file_format = file_type_selector(content_bytes)
            logger.info(f"Detected file format: {file_format}")
            
            # Create TransactionFile entity
            dto_data = {
                'user_id': user_id,
                'file_name': file_name,
                'file_size': int(file_size),
                's3_key': s3_key,
                'file_format': file_format,
                'currency': None,  # Optional field in DTO
            }
            if parsed_account_id:
                dto_data['account_id'] = parsed_account_id
            
            transaction_file_create_dto = TransactionFileCreate(**dto_data)
            
            # Convert DTO to full TransactionFile entity with specified file_id
            transaction_file = transaction_file_create_dto.to_transaction_file(
                file_id=uuid.UUID(file_id)
            )
            
            logger.info(f"Created TransactionFile object with file_id: {transaction_file.file_id}")
            if transaction_file.account_id:
                logger.info(f"TransactionFile associated with account_id: {transaction_file.account_id}")
            
            # Process the file
            file_processor_response: FileProcessorResponse = process_file(transaction_file)
            logger.info(f"File processing complete. Message: {file_processor_response.message}, "
                       f"Tx Count: {file_processor_response.transaction_count}")
            
            # Update result
            result['success'] = True
            result['transaction_count'] = file_processor_response.transaction_count
            result['duplicate_count'] = file_processor_response.duplicate_count or 0
            
            # Get transaction IDs if we have transactions
            if file_processor_response.transactions:
                result['transaction_ids'] = [str(tx.transaction_id) for tx in file_processor_response.transactions]
            
            # Publish FileProcessedEvent if processing was successful and we have transactions
            if result['transaction_count'] > 0 and ENABLE_EVENT_PUBLISHING:
                try:
                    file_event = FileProcessedEvent(
                        user_id=user_id,
                        file_id=str(transaction_file.file_id),
                        account_id=str(transaction_file.account_id) if transaction_file.account_id else '',
                        transaction_count=result['transaction_count'],
                        duplicate_count=result['duplicate_count'],
                        processing_status='success',
                        transaction_ids=result['transaction_ids']
                    )
                    event_service.publish_event(file_event)
                    logger.info(f"FileProcessedEvent published for file {transaction_file.file_id} "
                               f"with {len(result['transaction_ids'])} transaction IDs")
                    
                except Exception as e:
                    logger.warning(f"Failed to publish FileProcessedEvent for user {user_id}: {str(e)}")
                    # Don't fail the file processing because of event publishing failure
            
            # Analytics processing is now handled by analytics_consumer via events
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing file {file_data.get('file_id', 'unknown')}: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            
            result['error_message'] = str(e)
            
            # Publish failure event if event publishing is enabled
            if ENABLE_EVENT_PUBLISHING:
                try:
                    file_event = FileProcessedEvent(
                        user_id=user_id,
                        file_id=file_data.get('file_id', ''),
                        account_id=file_data.get('account_id', ''),
                        transaction_count=0,
                        duplicate_count=0,
                        processing_status='failed',
                        error_message=str(e)
                    )
                    event_service.publish_event(file_event)
                    logger.info(f"FileProcessedEvent (failed) published for file processing error")
                except Exception as event_error:
                    logger.warning(f"Failed to publish failure event: {str(event_error)}")
            
            return result
    
    def _log_processing_metrics(self, event: BaseEvent, result: Dict[str, Any]):
        """Log metrics for monitoring and debugging"""
        try:
            metrics = {
                'event_type': event.event_type,
                'event_id': event.event_id,
                'user_id': event.user_id,
                'success': result['success'],
                'transaction_count': result['transaction_count'],
                'duplicate_count': result['duplicate_count'],
                'error_message': result.get('error_message')
            }
            
            # Log as structured JSON for CloudWatch insights
            logger.info(f"FILE_PROCESSING_METRICS: {json.dumps(metrics)}")
            
        except Exception as e:
            logger.warning(f"Failed to log processing metrics: {str(e)}")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for file upload events from EventBridge.
    
    Expected event format from EventBridge:
    {
        "version": "0",
        "id": "event-id",
        "detail-type": "Application Event",
        "source": "transaction.service",
        "detail": {
            "eventId": "...",
            "eventType": "file.uploaded",
            "userId": "...",
            "data": {
                "fileId": "...",
                "fileName": "...",
                "fileSize": 12345,
                "s3Key": "...",
                "accountId": "...",
                ...
            }
        }
    }
    """
    try:
        logger.info(f"File processor consumer received event: {json.dumps(event)}")
        
        consumer = FileProcessorEventConsumer()
        result = consumer.handle_eventbridge_event(event, context)
        
        logger.info(f"File processor consumer completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"File processor consumer failed: {str(e)}")
        logger.error(f"Event: {json.dumps(event)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        
        # Re-raise to trigger EventBridge retry logic and DLQ handling
        raise
