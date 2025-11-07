"""
Analytics Event Consumer Lambda

This Lambda function consumes events from EventBridge that should trigger analytics 
processing. It creates AnalyticsProcessingStatus records to queue analytics work
for the existing analytics processor.

Event Types Processed:
- file.processed: Medium priority (2)
- transaction.updated: Low priority (3) 
- transactions.deleted: Medium priority (2)
- account.created: Low priority (3)
- account.updated: Low priority (3)
- account.deleted: High priority (1)
"""

import json
import logging
import os
import traceback
from typing import Dict, Any, List, Optional

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
from consumers.base_consumer import BaseEventConsumer
from models.events import BaseEvent, FileDeletionVoteEvent
from models.analytics import AnalyticType, AnalyticsProcessingStatus
from utils.db_utils import store_analytics_status
from services.event_service import event_service

# Event publishing configuration
ENABLE_EVENT_PUBLISHING = os.environ.get('ENABLE_EVENT_PUBLISHING', 'true').lower() == 'true'


class AnalyticsEventConsumer(BaseEventConsumer):
    """Consumer for events that should trigger analytics processing"""
    
    # Priority mapping for different event types
    PRIORITY_MAP = {
        'file.processed': 2,        # Medium priority - bulk data changes
        'transaction.updated': 3,   # Low priority - single transaction change
        'transactions.deleted': 2,  # Medium priority - data removal
        'account.created': 3,       # Low priority - no transactions yet
        'account.updated': 3,       # Low priority - metadata changes only
        'account.deleted': 1,       # High priority - major data change
        'file.deletion.requested': 2  # Medium priority - prepare for file deletion
    }
    
    # Analytics types affected by each event type
    ANALYTICS_TYPE_MAP = {
        'file.processed': ['cash_flow', 'category_trends', 'financial_health', 'account_efficiency'],
        'transaction.updated': ['cash_flow'],  # Minimal impact for single transaction
        'transactions.deleted': ['cash_flow', 'category_trends', 'financial_health'],
        'account.created': [],  # No analytics until transactions exist
        'account.updated': [],  # Metadata only, no financial impact
        'account.deleted': ['cash_flow', 'category_trends', 'financial_health', 'account_efficiency'],
        'file.deletion.requested': ['cash_flow', 'category_trends', 'financial_health', 'account_efficiency']
    }
    
    def __init__(self):
        super().__init__("analytics_consumer")
    
    def should_process_event(self, event: BaseEvent) -> bool:
        """Only process events that affect analytics"""
        return event.event_type in self.PRIORITY_MAP
    
    def process_event(self, event: BaseEvent) -> None:
        """Trigger analytics processing for the event"""
        try:
            self._log_processing_start(event)
            
            event_type = event.event_type
            priority = self.PRIORITY_MAP.get(event_type, 3)
            analytics_types = self._get_analytics_types(event_type)
            
            # Create status records for each analytics type
            success_count = self._create_analytics_status_records(event, analytics_types, priority)
            
            self._log_processing_success(success_count)
            self._handle_deletion_vote_if_needed(event, 'proceed')
            self._log_event_metrics(event, success_count, len(analytics_types))
                
        except Exception as e:
            self._handle_processing_error(event, e)
            raise
    
    def _log_processing_start(self, event: BaseEvent) -> None:
        """Log the start of event processing"""
        event_type = event.event_type
        priority = self.PRIORITY_MAP.get(event_type, 3)
        analytics_types = self.ANALYTICS_TYPE_MAP.get(event_type, [])
        
        logger.info(f"Processing {event_type} event {event.event_id} for user {event.user_id}")
        logger.info(f"Priority: {priority}, Analytics types: {analytics_types}")
    
    def _get_analytics_types(self, event_type: str) -> List[str]:
        """Get analytics types for the given event type"""
        analytics_types = self.ANALYTICS_TYPE_MAP.get(event_type, [])
        
        # If no specific analytics types, refresh all types
        if not analytics_types:
            return [t.value for t in AnalyticType]
        
        return analytics_types
    
    def _create_analytics_status_records(self, event: BaseEvent, analytics_types: List[str], priority: int) -> int:
        """Create analytics status records for all analytics types"""
        success_count = 0
        
        for analytic_type_str in analytics_types:
            try:
                # Convert string to AnalyticType enum
                analytic_type = AnalyticType(analytic_type_str.lower())
                
                status_record = AnalyticsProcessingStatus(
                    userId=event.user_id,
                    analyticType=analytic_type,
                    lastComputedDate=None,  # Force recomputation
                    dataAvailableThrough=None,
                    computationNeeded=True,
                    processingPriority=priority
                )
                
                store_analytics_status(status_record)
                success_count += 1
                
                logger.debug(f"Created analytics status for {analytic_type.value}")
                
            except ValueError as e:
                logger.warning(f"Invalid analytic type '{analytic_type_str}': {str(e)}")
            except Exception as e:
                logger.error(f"Failed to create status for {analytic_type_str}: {str(e)}")
        
        return success_count
    
    def _log_processing_success(self, success_count: int) -> None:
        """Log successful processing"""
        logger.info(f"Successfully queued {success_count} analytics types for processing")
    
    def _handle_deletion_vote_if_needed(self, event: BaseEvent, decision: str, reason: Optional[str] = None) -> None:
        """Handle deletion vote publishing if this is a file deletion request"""
        if event.event_type == 'file.deletion.requested' and ENABLE_EVENT_PUBLISHING:
            try:
                self._publish_deletion_vote(event, decision, reason)
            except Exception as vote_error:
                logger.error(f"Failed to publish deletion vote: {str(vote_error)}")
                if decision == 'deny':
                    # Don't re-raise vote errors during error handling
                    pass
                else:
                    raise
    
    def _handle_processing_error(self, event: BaseEvent, error: Exception) -> None:
        """Handle processing errors with consistent logging and voting"""
        logger.error(f"Error processing analytics event {event.event_id}: {str(error)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        
        # Publish deny vote for coordination (if this is a file deletion request)
        self._handle_deletion_vote_if_needed(event, 'deny', str(error))
    
    def _log_event_metrics(self, event: BaseEvent, success_count: int, total_count: int):
        """Log metrics for monitoring and debugging"""
        try:
            metrics = {
                'event_type': event.event_type,
                'event_id': event.event_id,
                'user_id': event.user_id,
                'success_count': success_count,
                'total_count': total_count,
                'processing_time_ms': None  # Could add timing if needed
            }
            
            # Log as structured JSON for CloudWatch insights
            logger.info(f"ANALYTICS_METRICS: {json.dumps(metrics)}")
            
        except Exception as e:
            logger.warning(f"Failed to log metrics: {str(e)}")
    
    def _publish_deletion_vote(self, original_event: BaseEvent, decision: str, reason: Optional[str] = None):
        """Publish deletion vote event for coordination"""
        try:
            if not original_event.data or not original_event.data.get('fileId'):
                logger.error("Cannot publish deletion vote: missing fileId in original event")
                return
            
            file_id = original_event.data['fileId']
            request_id = original_event.data.get('requestId') or original_event.correlation_id or original_event.event_id
            
            vote_event = FileDeletionVoteEvent(
                user_id=original_event.user_id,
                file_id=file_id,
                request_id=request_id,
                voter=self.get_voter_id(),
                decision=decision,
                reason=reason
            )
            
            success = event_service.publish_event(vote_event)
            if success:
                logger.info(f"Published deletion vote for file {file_id}, decision: {decision}")
            else:
                logger.error(f"Failed to publish deletion vote for file {file_id}")
                
        except Exception as e:
            logger.error(f"Error publishing deletion vote: {str(e)}")
            raise


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for analytics events from EventBridge.
    
    Expected event format from EventBridge:
    {
        "version": "0",
        "id": "event-id",
        "detail-type": "Application Event",
        "source": "transaction.service",
        "detail": {
            "eventId": "...",
            "eventType": "file.processed",
            "userId": "...",
            "data": { ... }
        }
    }
    """
    try:
        logger.info(f"Analytics consumer received event: {json.dumps(event)}")
        
        consumer = AnalyticsEventConsumer()
        result = consumer.handle_eventbridge_event(event, context)
        
        logger.info(f"Analytics consumer completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Analytics consumer failed: {str(e)}")
        logger.error(f"Event: {json.dumps(event)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        
        # Return failure but don't raise - let EventBridge handle retries
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Analytics consumer failed',
                'message': str(e)
            })
        } 