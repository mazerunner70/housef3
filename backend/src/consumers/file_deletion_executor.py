"""
L5 - File Deletion Executor
Executes file deletion when all voters approve
"""

import os
import uuid
import traceback
from typing import Dict, Any, Optional
from datetime import datetime

from models.events import BaseEvent, FileDeletedEvent
from services.event_service import EventService
from utils.db_utils import get_transaction_file, delete_file_metadata, delete_transactions_for_file, update_account_derived_values, NotFound
from services.operation_tracking_service import operation_tracking_service, OperationStatus
from utils.s3_dao import delete_object
from consumers.base_consumer import BaseEventConsumer
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Environment configuration
ENABLE_EVENT_PUBLISHING = os.environ.get('ENABLE_EVENT_PUBLISHING', 'true').lower() == 'true'

# Initialize services
event_service = EventService()


class FileDeletionExecutor(BaseEventConsumer):
    """L5 - Deletion Executor: Executes file deletion when approved"""
    
    def __init__(self):
        super().__init__("file_deletion_executor")
    
    def should_process_event(self, event: BaseEvent) -> bool:
        """Process file deletion approval events"""
        return event.event_type == 'file.deletion.approved'
    
    def process_event(self, event: BaseEvent) -> None:
        """Execute file deletion after approval"""
        try:
            logger.info(f"Processing deletion approval event {event.event_id}")
            
            if event.event_type == 'file.deletion.approved':
                self._execute_approved_deletion(event)
            else:
                logger.warning(f"Unexpected event type: {event.event_type}")
                
        except Exception as e:
            logger.error(f"Error executing file deletion: {str(e)}")
            logger.error(f"Event: {event}")
            raise
    
    def _execute_approved_deletion(self, event: BaseEvent) -> None:
        """Execute the approved file deletion"""
        try:
            if not event.data:
                raise ValueError("No data in deletion approval event")
            
            file_id = event.data.get('fileId')
            request_id = event.data.get('requestId')
            approved_by = event.data.get('approvedBy', [])
            
            if not file_id or not request_id:
                raise ValueError(f"Missing required data: fileId={file_id}, requestId={request_id}")
            
            logger.info(f"Executing approved deletion for file {file_id} (request {request_id})")
            logger.info(f"Approved by voters: {approved_by}")
            
            # Update operation tracking to executing
            try:
                logger.info(f"FILE_DELETION_EXECUTOR: Updating operation to executing - operationId={request_id}")
                operation_tracking_service.update_operation_status(
                    operation_id=request_id,
                    status=OperationStatus.EXECUTING,
                    progress_percentage=85,
                    current_step=3,
                    step_description="Deleting file and transactions"
                )
                logger.info(f"FILE_DELETION_EXECUTOR: Successfully updated operation to executing - operationId={request_id}")
            except Exception as e:
                logger.error(f"FILE_DELETION_EXECUTOR: Error updating operation tracking to executing - operationId={request_id}: {str(e)}")
            
            # Get file information from database
            try:
                file = get_transaction_file(uuid.UUID(file_id))
                if not file:
                    raise NotFound("File not found")
            except NotFound:
                logger.warning(f"File {file_id} not found, may have been already deleted")
                # Update operation to completed (already deleted)
                try:
                    operation_tracking_service.update_operation_status(
                        operation_id=request_id,
                        status=OperationStatus.COMPLETED,
                        progress_percentage=100,
                        step_description="File was already deleted"
                    )
                except Exception as e:
                    logger.error(f"Error updating operation tracking for already deleted file: {str(e)}")
                return
            
            user_id = file.user_id
            account_id = file.account_id
            file_name = file.file_name
            
            # Execute the deletion
            self._perform_file_deletion(request_id, user_id, file_id, account_id, file_name, file)
            
        except Exception as e:
            logger.error(f"Error executing approved deletion: {str(e)}")
            raise
    
    def _perform_file_deletion(self, request_id: str, user_id: str, file_id: str, 
                              account_id: Optional[uuid.UUID], file_name: str, file) -> None:
        """Perform the actual file deletion steps"""
        try:
            # Count transactions before deletion
            transaction_count = 0
            try:
                transactions_deleted = delete_transactions_for_file(uuid.UUID(file_id))
                transaction_count = transactions_deleted
                logger.info(f"Deleted {transactions_deleted} transactions for file {file_id}")
            except Exception as tx_error:
                logger.error(f"Error deleting transactions: {str(tx_error)}")
                raise
            
            # Delete file content from S3
            if not delete_object(file.s3_key):
                raise Exception(f"Error deleting file from S3 with key {file.s3_key}")
            logger.info(f"Successfully deleted file {file_id} from S3 bucket")
            
            # Delete file metadata from DynamoDB
            try:
                delete_file_metadata(uuid.UUID(file_id))
                logger.info(f"Successfully deleted file {file_id} from DynamoDB table")
            except Exception as dynamo_error:
                logger.error(f"Error deleting file from DynamoDB: {str(dynamo_error)}")
                raise
            
            # Update derived values for the affected account
            if account_id:
                try:
                    update_account_derived_values(account_id, user_id)
                    logger.info(f"Updated derived values for account {account_id} after file deletion")
                except Exception as derived_error:
                    logger.error(f"Error updating derived values for account {account_id}: {str(derived_error)}")
                    # Don't fail the whole operation for this
            
            # Publish FileDeletedEvent for cleanup notifications
            if ENABLE_EVENT_PUBLISHING:
                try:
                    deleted_event = FileDeletedEvent(
                        user_id=user_id,
                        file_id=file_id,
                        account_id=str(account_id) if account_id else None,
                        file_name=file_name,
                        transaction_count=transaction_count,
                        request_id=request_id
                    )
                    event_service.publish_event(deleted_event)
                    logger.info(f"FileDeletedEvent published for file {file_id}")
                except Exception as e:
                    logger.warning(f"Failed to publish FileDeletedEvent: {str(e)}")
            
            # Update operation tracking to completed
            try:
                logger.info(f"FILE_DELETION_EXECUTOR: Updating operation to completed - operationId={request_id}")
                operation_tracking_service.update_operation_status(
                    operation_id=request_id,
                    status=OperationStatus.COMPLETED,
                    progress_percentage=100,
                    current_step=4,
                    step_description="File deletion completed successfully"
                )
                logger.info(f"FILE_DELETION_EXECUTOR: Successfully updated operation to completed - operationId={request_id}")
            except Exception as e:
                logger.error(f"FILE_DELETION_EXECUTOR: Error updating operation tracking to completed - operationId={request_id}: {str(e)}")
            
            logger.info(f"File deletion completed successfully for file {file_id} (request {request_id})")
            
        except Exception as e:
            logger.error(f"Error performing file deletion for request {request_id}: {str(e)}")
            logger.error(f"Stacktrace: {traceback.format_exc()}")
            
            # Update operation tracking to failed
            try:
                logger.info(f"FILE_DELETION_EXECUTOR: Updating operation to failed - operationId={request_id}")
                operation_tracking_service.update_operation_status(
                    operation_id=request_id,
                    status=OperationStatus.FAILED,
                    error_message=f"Deletion failed: {str(e)}"
                )
                logger.info(f"FILE_DELETION_EXECUTOR: Successfully updated operation to failed - operationId={request_id}")
            except Exception as tracking_error:
                logger.error(f"FILE_DELETION_EXECUTOR: Error updating operation tracking to failed - operationId={request_id}: {str(tracking_error)}")
            
            raise


def handler(event, context):
    """Lambda handler for file deletion executor"""
    consumer = FileDeletionExecutor()
    return consumer.handle_eventbridge_event(event, context)
