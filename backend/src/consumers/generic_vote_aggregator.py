"""
Generic Vote Aggregator
Handles voting workflows for any business process (file deletion, file upload, account changes, etc.)
"""

import os
import uuid
import logging
import traceback
from typing import Dict, Any, Optional, Set, List
from datetime import datetime, timedelta
from decimal import Decimal

from models.events import BaseEvent
from services.event_service import EventService
from services.vote_service import vote_service
from consumers.base_consumer import BaseEventConsumer

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment configuration
ENABLE_EVENT_PUBLISHING = os.environ.get('ENABLE_EVENT_PUBLISHING', 'true').lower() == 'true'
VOTE_TIMEOUT_MINUTES = int(os.environ.get('VOTE_TIMEOUT_MINUTES', '5'))

# Initialize services
event_service = EventService()


# Removed GenericVoteAggregator class - logic moved to VoteService


def convert_decimals(obj: Any) -> Any:
    """Convert Decimal objects to appropriate Python types for JSON serialization"""
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(v) for v in obj]
    elif isinstance(obj, Decimal):
        # Convert to int if it's a whole number, otherwise float
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj


class GenericVoteAggregatorConsumer(BaseEventConsumer):
    """Generic Vote Aggregator: Handles voting for any workflow type"""
    
    def __init__(self):
        super().__init__("generic_vote_aggregator")
    
    def should_process_event(self, event: BaseEvent) -> bool:
        """Process any voting-related events"""
        # Handle request events (*.requested) and vote events (*.vote)
        return (event.event_type.endswith('.requested') or 
                event.event_type.endswith('.vote'))
    
    def process_event(self, event: BaseEvent) -> None:
        """Process voting events for any workflow"""
        try:
            logger.info(f"Processing {event.event_type} event {event.event_id}")
            
            if event.event_type.endswith('.requested'):
                self._handle_workflow_request(event)
            elif event.event_type.endswith('.vote'):
                self._handle_vote(event)
            else:
                logger.warning(f"Unexpected event type: {event.event_type}")
                
        except Exception as e:
            logger.error(f"Error processing vote aggregation event: {str(e)}")
            logger.error(f"Event: {event}")
            raise
    
    def _handle_workflow_request(self, event: BaseEvent) -> None:
        """Handle initial workflow request - set up vote tracking"""
        try:
            if not event.data:
                raise ValueError("Event data is required for workflow request")
                
            # Extract workflow type from event type (e.g., 'file.deletion.requested' -> 'file.deletion')
            workflow_type = '.'.join(event.event_type.split('.')[:-1])
            
            # Extract entity ID based on workflow type
            if workflow_type == 'file.deletion':
                entity_id = event.data.get('fileId')
                request_id = event.data.get('requestId')
            elif workflow_type == 'file.upload':
                entity_id = event.data.get('fileId') or event.data.get('fileName')
                request_id = event.data.get('requestId')
            elif workflow_type == 'account.modification':
                entity_id = event.data.get('accountId')
                request_id = event.data.get('requestId')
            else:
                # Generic fallback
                entity_id = event.data.get('entityId') or event.data.get('id')
                request_id = event.data.get('requestId')
            
            if not entity_id or not request_id:
                raise ValueError(f"Missing entity_id or request_id for {workflow_type}")
            
            # Register the vote tracking
            vote_service.register_vote_request(
                workflow_type=workflow_type,
                entity_id=entity_id,
                request_id=request_id,
                user_id=event.user_id,
                context=event.data
            )
            
        except Exception as e:
            logger.error(f"Error handling workflow request: {str(e)}")
            raise
    
    def _handle_vote(self, event: BaseEvent) -> None:
        """Handle vote from a voter - check if decision can be made"""
        try:
            if not event.data:
                raise ValueError("Event data is required for vote")
                
            # Extract workflow type from event type
            workflow_type = '.'.join(event.event_type.split('.')[:-1])
            
            entity_id = event.data.get('fileId') or event.data.get('accountId') or event.data.get('entityId')
            request_id = event.data.get('requestId')
            voter = event.data.get('voter')
            decision = event.data.get('decision')
            reason = event.data.get('reason') or ''
            
            if not all([entity_id, request_id, voter, decision]):
                raise ValueError(f"Missing required vote data: entity_id={entity_id}, request_id={request_id}, voter={voter}, decision={decision}")
            
            # Business rule: deny votes must have a reason
            if decision == 'deny' and not reason.strip():
                raise ValueError(f"Denial votes must include a reason. Voter: {voter}, Entity: {entity_id}")
            
            # Type assertions for mypy
            assert isinstance(entity_id, str)
            assert isinstance(request_id, str)
            assert isinstance(voter, str)
            assert isinstance(decision, str)
            assert isinstance(reason, str)
            
            final_decision = vote_service.record_vote(
                workflow_type=workflow_type,
                entity_id=entity_id,
                request_id=request_id,
                voter=voter,
                decision=decision,
                reason=reason
            )
            
            if final_decision == 'approved':
                self._publish_approval(workflow_type, entity_id, request_id)
            elif final_decision == 'denied':
                self._publish_denial(workflow_type, entity_id, request_id, voter, reason)
            # If final_decision is None, we're still waiting for more votes
            
        except Exception as e:
            logger.error(f"Error handling vote: {str(e)}")
            raise
    
    def _publish_approval(self, workflow_type: str, entity_id: str, request_id: str) -> None:
        """Publish approval event when all voters approve"""
        try:
            if not ENABLE_EVENT_PUBLISHING:
                logger.warning("Event publishing disabled, skipping approval event")
                return
            
            # Get full vote information
            vote_info = vote_service.get_vote_info(workflow_type, entity_id, request_id)
            if not vote_info:
                logger.error(f"Could not get vote info for {workflow_type}#{entity_id}#{request_id}")
                return
            
            config = vote_service.get_workflow_config(workflow_type)
            approved_event_type = config.get('approved_event', f'{workflow_type}.approved')
            
            # Create generic approval event
            approval_event_data = {
                'entityId': entity_id,
                'requestId': request_id,
                'workflowType': workflow_type,
                'approvedBy': list(vote_info['votesReceived'].keys()),
                'allVotes': vote_info['votesReceived'],
                'context': vote_info.get('context', {})
            }
            
            # Add workflow-specific fields
            if workflow_type == 'file.deletion':
                approval_event_data['fileId'] = entity_id
            elif workflow_type == 'account.modification':
                approval_event_data['accountId'] = entity_id
            
            # Publish using event service (would need to create dynamic event)
            self._publish_dynamic_event(
                event_type=approved_event_type,
                user_id=vote_info['userId'],
                data=approval_event_data
            )
            
            logger.info(f"Published {workflow_type} approval for {entity_id}")
            
            # Clean up vote record
            vote_service.cleanup_vote_record(workflow_type, entity_id, request_id)
            
        except Exception as e:
            logger.error(f"Error publishing approval: {str(e)}")
            raise
    
    def _publish_denial(self, workflow_type: str, entity_id: str, request_id: str, 
                       denied_by: str, reason: str) -> None:
        """Publish denial event when any voter denies"""
        try:
            if not ENABLE_EVENT_PUBLISHING:
                logger.warning("Event publishing disabled, skipping denial event")
                return
            
            # Get full vote information
            vote_info = vote_service.get_vote_info(workflow_type, entity_id, request_id)
            if not vote_info:
                logger.error(f"Could not get vote info for {workflow_type}#{entity_id}#{request_id}")
                return
            
            config = vote_service.get_workflow_config(workflow_type)
            denied_event_type = config.get('denied_event', f'{workflow_type}.denied')
            
            # Create generic denial event
            denial_event_data = {
                'entityId': entity_id,
                'requestId': request_id,
                'workflowType': workflow_type,
                'deniedBy': denied_by,
                'reason': reason,
                'allVotes': vote_info['votesReceived'],
                'context': vote_info.get('context', {})
            }
            
            # Add workflow-specific fields
            if workflow_type == 'file.deletion':
                denial_event_data['fileId'] = entity_id
            elif workflow_type == 'account.modification':
                denial_event_data['accountId'] = entity_id
            
            self._publish_dynamic_event(
                event_type=denied_event_type,
                user_id=vote_info['userId'],
                data=denial_event_data
            )
            
            logger.info(f"Published {workflow_type} denial for {entity_id}: {reason}")
            
            # Clean up vote record
            vote_service.cleanup_vote_record(workflow_type, entity_id, request_id)
            
        except Exception as e:
            logger.error(f"Error publishing denial: {str(e)}")
            raise
    
    def _publish_dynamic_event(self, event_type: str, user_id: str, data: Dict[str, Any]) -> None:
        """Publish a dynamic event (would need BaseEvent enhancement)"""
        # For now, use a simple approach - in production you'd want a more dynamic event system
        from models.events import BaseEvent
        
        # Convert any Decimal objects to JSON-serializable types
        clean_data = convert_decimals(data)
        
        event = BaseEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='vote.aggregator',
            user_id=user_id,
            data=clean_data
        )
        
        event_service.publish_event(event)


def handler(event, context):
    """Lambda handler for generic vote aggregator"""
    consumer = GenericVoteAggregatorConsumer()
    return consumer.handle_eventbridge_event(event, context)
