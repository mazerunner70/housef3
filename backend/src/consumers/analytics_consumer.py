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
import sys
import traceback
from typing import Dict, Any, List, Optional

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
from models.events import BaseEvent
from models.analytics import AnalyticType, AnalyticsProcessingStatus
from utils.db_utils import store_analytics_status


class AnalyticsEventConsumer(BaseEventConsumer):
    """Consumer for events that should trigger analytics processing"""
    
    # Priority mapping for different event types
    PRIORITY_MAP = {
        'file.processed': 2,        # Medium priority - bulk data changes
        'transaction.updated': 3,   # Low priority - single transaction change
        'transactions.deleted': 2,  # Medium priority - data removal
        'account.created': 3,       # Low priority - no transactions yet
        'account.updated': 3,       # Low priority - metadata changes only
        'account.deleted': 1        # High priority - major data change
    }
    
    # Analytics types affected by each event type
    ANALYTICS_TYPE_MAP = {
        'file.processed': ['cash_flow', 'category_trends', 'financial_health', 'account_efficiency'],
        'transaction.updated': ['cash_flow'],  # Minimal impact for single transaction
        'transactions.deleted': ['cash_flow', 'category_trends', 'financial_health'],
        'account.created': [],  # No analytics until transactions exist
        'account.updated': [],  # Metadata only, no financial impact
        'account.deleted': ['cash_flow', 'category_trends', 'financial_health', 'account_efficiency']
    }
    
    def __init__(self):
        super().__init__("analytics_consumer")
    
    def should_process_event(self, event: BaseEvent) -> bool:
        """Only process events that affect analytics"""
        return event.event_type in self.PRIORITY_MAP
    
    def process_event(self, event: BaseEvent) -> None:
        """Trigger analytics processing for the event"""
        try:
            event_type = event.event_type
            priority = self.PRIORITY_MAP.get(event_type, 3)
            analytics_types = self.ANALYTICS_TYPE_MAP.get(event_type, [])
            
            logger.info(f"Processing {event_type} event {event.event_id} for user {event.user_id}")
            logger.info(f"Priority: {priority}, Analytics types: {analytics_types}")
            
            # If no specific analytics types, refresh all types
            if not analytics_types:
                analytics_types = [t.value for t in AnalyticType]
            else:
                # Convert string values to AnalyticType enum values
                analytics_types = [t for t in analytics_types]
            
            # Create status records for each analytics type
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
            
            logger.info(f"Successfully queued {success_count} analytics types for processing")
            
            # Log event details for monitoring
            self._log_event_metrics(event, success_count, len(analytics_types))
                
        except Exception as e:
            logger.error(f"Error processing analytics event {event.event_id}: {str(e)}")
            logger.error(f"Stacktrace: {traceback.format_exc()}")
            raise
    
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