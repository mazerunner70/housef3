"""
Workflow Tracking Consumer
Listens to deletion-related events and updates workflow progress for frontend polling
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from consumers.base_consumer import BaseEventConsumer
from models.events import BaseEvent
from services.operation_tracking_service import operation_tracking_service, OperationType, OperationStatus

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class WorkflowTrackingConsumer(BaseEventConsumer):
    """
    Event-driven workflow tracking consumer
    
    Listens to all deletion-related events and updates workflow progress:
    - file.deletion.requested (10% - Request initiated)
    - categorization.vote.submitted (30% - Categorization consumer voted)
    - analytics.vote.submitted (50% - Analytics consumer voted) 
    - file.deletion.approved (70% - All votes collected, deletion approved)
    - file.deletion.completed (100% - File actually deleted)
    """
    
    def __init__(self):
        super().__init__(consumer_name="workflow_tracking")
        
        # Event type to progress mapping
        self.progress_mapping = {
            'file.deletion.requested': {
                'progress': 10,
                'status': OperationStatus.INITIATED,
                'description': 'File deletion request received'
            },
            'file.deletion.vote': {
                'progress': None,  # Will be calculated based on votes received
                'status': OperationStatus.WAITING_FOR_APPROVAL,
                'description': 'Collecting voter approvals'
            },
            'file.deletion.approved': {
                'progress': 70,
                'status': OperationStatus.APPROVED,
                'description': 'All approvals received, executing deletion'
            },
            'file.deletion.denied': {
                'progress': None,  # Keep current progress
                'status': OperationStatus.DENIED,
                'description': 'File deletion denied by voters'
            },
            'file.deleted': {
                'progress': 100,
                'status': OperationStatus.COMPLETED,
                'description': 'File successfully deleted'
            }
        }
    
    def get_supported_event_types(self) -> List[str]:
        """Return list of event types this consumer processes"""
        return list(self.progress_mapping.keys())
    
    def should_process_event(self, event: BaseEvent) -> bool:
        """Check if this consumer should process the given event"""
        return event.event_type in self.progress_mapping
    
    def process_event(self, event: BaseEvent) -> None:
        """Process deletion-related events and update workflow tracking"""
        try:
            logger.info(f"WORKFLOW_TRACKING: Processing event - type={event.event_type}, eventId={event.event_id}")
            
            # Extract operation details from the event
            operation_id, entity_id, user_id = self._extract_operation_details(event)
            
            logger.info(f"WORKFLOW_TRACKING: Extracted details - operationId={operation_id}, entityId={entity_id}, userId={user_id}")
            
            if not operation_id:
                logger.warning(f"No operation ID found in event {event.event_id}")
                return
            
            progress_info = self.progress_mapping.get(event.event_type)
            if not progress_info:
                logger.warning(f"No progress mapping for event type: {event.event_type}")
                return
            
            # Handle operation initialization for file.deletion.requested
            if event.event_type == 'file.deletion.requested':
                logger.info(f"WORKFLOW_TRACKING: Initializing new operation for deletion request - requestId={operation_id}")
                # Initialize operation and get the actual operation ID created
                actual_operation_id = self._initialize_operation(operation_id, entity_id, user_id, event)
                if actual_operation_id:
                    logger.info(f"WORKFLOW_TRACKING: Operation initialized - originalRequestId={operation_id}, actualOperationId={actual_operation_id}")
                    # Use the actual operation ID for progress update
                    operation_id = actual_operation_id
                else:
                    logger.error(f"WORKFLOW_TRACKING: Failed to initialize operation for requestId={operation_id}")
            
            # Handle special vote counting logic
            if event.event_type == 'file.deletion.vote':
                logger.info(f"WORKFLOW_TRACKING: Handling vote progress for operationId={operation_id}")
                self._handle_vote_progress(operation_id, event)
            else:
                # Update operation progress normally
                logger.info(f"WORKFLOW_TRACKING: Updating operation progress - operationId={operation_id}, status={progress_info['status']}, progress={progress_info['progress']}%")
                self._update_operation_progress(operation_id, progress_info, event)
            
            logger.info(f"WORKFLOW_TRACKING: Successfully processed event - operationId={operation_id}, progress={progress_info['progress']}%")
            
        except Exception as e:
            logger.error(f"Error processing workflow tracking event: {str(e)}")
            logger.error(f"Event: {event}")
            raise
    
    def _extract_operation_details(self, event: BaseEvent) -> tuple:
        """Extract operation ID, entity ID, and user ID from event"""
        operation_id = None
        entity_id = None
        user_id = None
        
        if hasattr(event, 'data') and event.data:
            # Try different field names based on event type
            operation_id = event.data.get('requestId') or event.data.get('operationId')
            entity_id = event.data.get('fileId') or event.data.get('entityId')
            user_id = event.data.get('userId')
        
        # For file.deletion.requested and file.deleted events, also check user_id from event
        if event.event_type in ['file.deletion.requested', 'file.deleted']:
            user_id = event.user_id
        
        return operation_id, entity_id, user_id
    
    def _initialize_operation(self, operation_id: str, entity_id: str, user_id: str, event: BaseEvent) -> Optional[str]:
        """Initialize operation tracking record for new deletion request"""
        try:
            # Extract context from the event
            context = {}
            if hasattr(event, 'data') and event.data:
                context = {
                    'fileName': event.data.get('fileName'),
                    'fileSize': event.data.get('fileSize'),
                    'transactionCount': event.data.get('transactionCount'),
                    'accountId': event.data.get('accountId'),
                    'userId': user_id
                }
            
            # Start operation tracking with existing operation ID
            actual_operation_id = operation_tracking_service.start_operation(
                operation_type=OperationType.FILE_DELETION,
                entity_id=entity_id,
                user_id=user_id,
                context=context,
                operation_id=operation_id  # Reuse the existing operation ID from the event
            )
            
            logger.info(f"Initialized workflow tracking: {actual_operation_id}")
            return actual_operation_id
            
        except Exception as e:
            logger.error(f"Error initializing workflow tracking: {str(e)}")
            # Don't re-raise - workflow tracking failure shouldn't stop the deletion flow
            return None
    
    def _update_operation_progress(self, operation_id: str, progress_info: Dict[str, Any], event: BaseEvent) -> None:
        """Update operation progress and status"""
        try:
            update_params = {
                'operation_id': operation_id,
                'status': progress_info['status'],
                'step_description': progress_info['description']
            }
            
            # Only update progress if specified (failed events keep current progress)
            if progress_info['progress'] is not None:
                update_params['progress_percentage'] = progress_info['progress']
            
            # Add error message for failed operations
            if progress_info['status'] == OperationStatus.FAILED:
                error_msg = "File deletion failed"
                if hasattr(event, 'data') and event.data:
                    error_msg = event.data.get('errorMessage', error_msg)
                update_params['error_message'] = error_msg
            
            operation_tracking_service.update_operation_status(**update_params)
            
        except Exception as e:
            logger.error(f"Error updating operation progress: {str(e)}")
            # Don't re-raise - workflow tracking failure shouldn't stop the deletion flow
    
    def _handle_vote_progress(self, operation_id: str, event: BaseEvent) -> None:
        """Handle vote events and calculate progress based on votes received"""
        try:
            if not event.data:
                return
            
            voter = event.data.get('voter', 'unknown')
            decision = event.data.get('decision', 'unknown')
            
            # Simple progress calculation: each vote adds 20%
            # Starting at 10% (from initial request), so:
            # 1 vote = 30%, 2 votes = 50%
            vote_progress_map = {
                'analytics_consumer': 30,
                'categorization_consumer': 50
            }
            
            progress = vote_progress_map.get(voter, 30)  # Default to 30% for unknown voters
            
            description = f"Vote received from {voter.replace('_', ' ')}: {decision}"
            
            operation_tracking_service.update_operation_status(
                operation_id=operation_id,
                status=OperationStatus.WAITING_FOR_APPROVAL,
                progress_percentage=progress,
                step_description=description
            )
            
            logger.info(f"Updated operation {operation_id} with vote from {voter}: {progress}%")
            
        except Exception as e:
            logger.error(f"Error handling vote progress: {str(e)}")
            # Don't re-raise - workflow tracking failure shouldn't stop the deletion flow


# Global consumer instance
workflow_tracking_consumer = WorkflowTrackingConsumer()


def handler(event, context):
    """Lambda handler function"""
    return workflow_tracking_consumer.handle_eventbridge_event(event, context)
