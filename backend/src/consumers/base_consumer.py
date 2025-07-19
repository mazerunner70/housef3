"""
Base consumer framework for event-driven architecture.
Provides common functionality for all event consumers including event parsing, 
error handling, metrics, and Lambda integration.
"""
import json
import logging
import os
import traceback
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from models.events import BaseEvent

logger = logging.getLogger(__name__)


class EventProcessingError(Exception):
    """Custom exception for event processing errors"""
    def __init__(self, message: str, event_id: Optional[str] = None, permanent: bool = False):
        super().__init__(message)
        self.event_id = event_id
        self.permanent = permanent


class BaseEventConsumer(ABC):
    """
    Base class for all event consumers.
    
    Provides common functionality including:
    - Event parsing from EventBridge/SQS format
    - Error handling and classification
    - Metrics and logging
    - Idempotency support
    - Lambda context handling
    """
    
    def __init__(self, consumer_name: str, enable_metrics: bool = True):
        """
        Initialize the base consumer.
        
        Args:
            consumer_name: Name of the consumer for logging/metrics
            enable_metrics: Whether to collect processing metrics
        """
        self.consumer_name = consumer_name
        self.enable_metrics = enable_metrics
        self.processed_events = set()  # For basic idempotency
        self._lambda_context: Optional[Any] = None  # Lambda context for response metadata
        
        # Configure logging
        logger.info(f"Initializing {consumer_name} consumer")
        
    def handle_eventbridge_event(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Main handler for EventBridge events.
        This is the entry point called by AWS Lambda.
        
        Args:
            event: EventBridge event payload
            context: Lambda context object
            
        Returns:
            dict: Processing results and metrics
        """
        start_time = datetime.now()
        stats = {
            'consumer': self.consumer_name,
            'processed_count': 0,
            'failed_count': 0,
            'skipped_count': 0,
            'errors': []
        }
        
        try:
            logger.info(f"🔄 {self.consumer_name} processing event batch")
            
            # Handle both direct EventBridge events and SQS-wrapped events
            records = self._extract_records(event)
            
            if not records:
                logger.warning("No records found in event payload")
                return self._create_response(stats, start_time)
            
            logger.info(f"Processing {len(records)} records")
            
            # Process each record
            for record in records:
                try:
                    # Parse the event
                    parsed_event = self._parse_event_record(record)
                    
                    # Check if we should process this event
                    if not self.should_process_event(parsed_event):
                        logger.debug(f"Skipping event {parsed_event.event_id} - doesn't match criteria")
                        stats['skipped_count'] += 1
                        continue
                    
                    # Check for duplicate processing (basic idempotency)
                    if self._is_duplicate_event(parsed_event):
                        logger.info(f"Skipping duplicate event {parsed_event.event_id}")
                        stats['skipped_count'] += 1
                        continue
                    
                    # Process the event
                    logger.debug(f"Processing event {parsed_event.event_id} of type {parsed_event.event_type}")
                    self.process_event(parsed_event)
                    
                    # Mark as processed
                    self._mark_event_processed(parsed_event)
                    stats['processed_count'] += 1
                    
                    logger.debug(f"✅ Successfully processed event {parsed_event.event_id}")
                    
                except EventProcessingError as e:
                    logger.error(f"❌ EventProcessingError: {str(e)}")
                    stats['failed_count'] += 1
                    stats['errors'].append({
                        'event_id': e.event_id,
                        'error': str(e),
                        'permanent': e.permanent
                    })
                    
                    # Re-raise permanent failures for DLQ routing
                    if e.permanent:
                        raise
                        
                except Exception as e:
                    error_msg = f"Unexpected error processing record: {str(e)}"
                    logger.error(error_msg)
                    logger.error(traceback.format_exc())
                    
                    stats['failed_count'] += 1
                    stats['errors'].append({
                        'event_id': getattr(parsed_event, 'event_id', 'unknown') if 'parsed_event' in locals() else 'unknown',
                        'error': str(e),
                        'permanent': self.is_permanent_failure(e)
                    })
                    
                    # Re-raise if permanent failure
                    if self.is_permanent_failure(e):
                        raise
            
            # Log final statistics
            total_events = stats['processed_count'] + stats['failed_count'] + stats['skipped_count']
            logger.info(f"✅ {self.consumer_name} processing complete: "
                       f"{stats['processed_count']}/{total_events} processed, "
                       f"{stats['failed_count']} failed, "
                       f"{stats['skipped_count']} skipped")
            
            return self._create_response(stats, start_time)
            
        except Exception as e:
            logger.error(f"❌ {self.consumer_name} failed with critical error: {str(e)}")
            logger.error(traceback.format_exc())
            
            stats['errors'].append({
                'error': str(e),
                'critical': True
            })
            
            return self._create_response(stats, start_time, status_code=500)
    
    def _extract_records(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract records from different event formats"""
        # Direct EventBridge event
        if 'source' in event and 'detail-type' in event:
            return [event]
        
        # SQS event with multiple records
        if 'Records' in event:
            return event['Records']
        
        # Batch of EventBridge events
        if isinstance(event, list):
            return event
        
        # Single event in a wrapper
        return [event]
    
    def _parse_event_record(self, record: Dict[str, Any]) -> BaseEvent:
        """Parse EventBridge record into BaseEvent"""
        try:
            # Direct EventBridge event
            if 'detail' in record and 'source' in record:
                detail = record['detail']
                if isinstance(detail, str):
                    detail = json.loads(detail)
                
                return BaseEvent(
                    event_id=detail.get('eventId', ''),
                    event_type=record.get('detail-type', ''),
                    event_version=detail.get('eventVersion', '1.0'),
                    timestamp=detail.get('timestamp', 0),
                    source=record.get('source', ''),
                    user_id=detail.get('userId', ''),
                    correlation_id=detail.get('correlationId'),
                    causation_id=detail.get('causationId'),
                    data=detail.get('data', {}),
                    metadata=detail.get('metadata', {})
                )
            
            # SQS wrapped EventBridge event
            if 'body' in record:
                body = json.loads(record['body'])
                
                # EventBridge event in SQS body
                if 'detail' in body and 'source' in body:
                    return self._parse_event_record(body)
                
                # Direct event data in SQS body
                return BaseEvent(
                    event_id=body.get('eventId', ''),
                    event_type=body.get('eventType', ''),
                    event_version=body.get('eventVersion', '1.0'),
                    timestamp=body.get('timestamp', 0),
                    source=body.get('source', ''),
                    user_id=body.get('userId', ''),
                    correlation_id=body.get('correlationId'),
                    causation_id=body.get('causationId'),
                    data=body.get('data', {}),
                    metadata=body.get('metadata', {})
                )
            
            # Unknown format
            raise EventProcessingError(
                f"Unknown event record format: {list(record.keys())}",
                permanent=True
            )
            
        except json.JSONDecodeError as e:
            raise EventProcessingError(
                f"Failed to parse JSON in event record: {str(e)}",
                permanent=True
            )
        except Exception as e:
            raise EventProcessingError(
                f"Failed to parse event record: {str(e)}",
                permanent=True
            )
    
    def _is_duplicate_event(self, event: BaseEvent) -> bool:
        """Basic duplicate detection using in-memory set"""
        return event.event_id in self.processed_events
    
    def _mark_event_processed(self, event: BaseEvent) -> None:
        """Mark event as processed for duplicate detection"""
        self.processed_events.add(event.event_id)
        
        # Prevent memory growth in long-running containers
        if len(self.processed_events) > 1000:
            # Keep only the most recent 500 events
            recent_events = list(self.processed_events)[-500:]
            self.processed_events = set(recent_events)
    
    def _create_response(self, stats: Dict[str, Any], start_time: datetime, status_code: int = 200) -> Dict[str, Any]:
        """Create standardized response with metrics"""
        processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        response = {
            'statusCode': status_code,
            'consumer': self.consumer_name,
            'processingTimeMs': round(processing_time_ms, 2),
            'timestamp': int(datetime.now().timestamp() * 1000),
            **stats
        }
        
        # Add Lambda context info if available
        if hasattr(self, '_lambda_context'):
            response['requestId'] = getattr(self._lambda_context, 'aws_request_id', None)
            response['remainingTimeMs'] = getattr(self._lambda_context, 'get_remaining_time_in_millis', lambda: None)()
        
        return response
    
    # =============================================================================
    # ABSTRACT METHODS - Must be implemented by subclasses
    # =============================================================================
    
    @abstractmethod
    def should_process_event(self, event: BaseEvent) -> bool:
        """
        Determine if this consumer should process the event.
        
        Args:
            event: The parsed event
            
        Returns:
            bool: True if the event should be processed
        """
        pass
    
    @abstractmethod
    def process_event(self, event: BaseEvent) -> None:
        """
        Process the event. This is where the main business logic goes.
        
        Args:
            event: The parsed event to process
            
        Raises:
            EventProcessingError: For application-specific errors
            Exception: For unexpected errors
        """
        pass
    
    # =============================================================================
    # OPTIONAL METHODS - Can be overridden by subclasses
    # =============================================================================
    
    def is_permanent_failure(self, error: Exception) -> bool:
        """
        Determine if error is permanent (for DLQ routing).
        Override in subclasses for specific error handling.
        
        Args:
            error: The exception that occurred
            
        Returns:
            bool: True if this is a permanent failure
        """
        # Default implementation considers certain error types permanent
        permanent_error_types = (
            ValueError,           # Bad input data
            TypeError,           # Wrong data types  
            KeyError,            # Missing required fields
            AttributeError,      # Missing attributes
            json.JSONDecodeError # Invalid JSON
        )
        
        return isinstance(error, permanent_error_types)
    
    def get_event_priority(self, event: BaseEvent) -> int:
        """
        Get processing priority for the event (1=highest, 5=lowest).
        Override in subclasses for priority-based processing.
        
        Args:
            event: The event to get priority for
            
        Returns:
            int: Priority level (1-5)
        """
        return 3  # Default medium priority
    
    def validate_event(self, event: BaseEvent) -> bool:
        """
        Validate event data before processing.
        Override in subclasses for custom validation.
        
        Args:
            event: The event to validate
            
        Returns:
            bool: True if event is valid
            
        Raises:
            EventProcessingError: If validation fails
        """
        # Basic validation
        if not event.event_id:
            raise EventProcessingError("Event ID is required", permanent=True)
        
        if not event.event_type:
            raise EventProcessingError("Event type is required", permanent=True)
        
        if not event.user_id:
            raise EventProcessingError("User ID is required", permanent=True)
        
        return True
    
    def setup_consumer(self) -> None:
        """
        One-time setup for the consumer.
        Override in subclasses for initialization logic.
        """
        pass
    
    def cleanup_consumer(self) -> None:
        """
        Cleanup when consumer shuts down.
        Override in subclasses for cleanup logic.
        """
        pass


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_lambda_handler(consumer_class, *args, **kwargs):
    """
    Factory function to create a Lambda handler from a consumer class.
    
    Args:
        consumer_class: The consumer class to instantiate
        *args, **kwargs: Arguments to pass to the consumer constructor
        
    Returns:
        function: Lambda handler function
    """
    consumer = None
    
    def lambda_handler(event, context):
        nonlocal consumer
        
        # Lazy initialization
        if consumer is None:
            consumer = consumer_class(*args, **kwargs)
            consumer.setup_consumer()
            logger.info(f"Initialized {consumer.consumer_name} consumer")
        
        # Store context for response metadata
        consumer._lambda_context = context
        
        try:
            return consumer.handle_eventbridge_event(event, context)
        except Exception as e:
            logger.error(f"Critical error in {consumer.consumer_name}: {str(e)}")
            return {
                'statusCode': 500,
                'error': str(e),
                'consumer': consumer.consumer_name,
                'timestamp': int(datetime.now().timestamp() * 1000)
            }
    
    return lambda_handler 