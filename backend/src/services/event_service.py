"""
Event publishing service for the event-driven architecture.
Handles publishing events with batching, error handling, and retry logic.
"""
import logging
import time
from typing import List, Optional, Dict, Any
from models.events import BaseEvent
from datetime import datetime
from utils.event_dao import (
    publish_event_to_eventbridge,
    publish_events_batch_to_eventbridge,
    eventbridge_health_check,
    get_event_bus_name
)

logger = logging.getLogger(__name__)


class EventService:
    """Service for publishing events with batching and retry logic"""
    
    def __init__(self):
        """Initialize the EventService."""
        self.event_bus_name = get_event_bus_name()
        logger.info(f"EventService initialized with bus: {self.event_bus_name}")
    
    def publish_event(self, event: BaseEvent) -> bool:
        """
        Publish a single event.
        
        Args:
            event: The event to publish
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert event to EventBridge format
            eventbridge_entry = event.to_eventbridge_format()
            
            logger.debug(f"Publishing event {event.event_id} of type {event.event_type}")
            
            success = publish_event_to_eventbridge(eventbridge_entry)
            
            if success:
                logger.info(f"Successfully published event {event.event_id} of type {event.event_type}")
            else:
                logger.error(f"Failed to publish event {event.event_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Unexpected error publishing event {event.event_id}: {str(e)}")
            return False
    
    def publish_events_batch(self, events: List[BaseEvent]) -> int:
        """
        Publish multiple events in batches.
        EventBridge supports up to 10 events per batch.
        
        Args:
            events: List of events to publish
            
        Returns:
            int: Number of events successfully published
        """
        if not events:
            logger.warning("No events provided for batch publishing")
            return 0
        
        total_events = len(events)
        successful_count = 0
        
        logger.info(f"Starting batch publishing of {total_events} events")
        
        # Process events in batches of 10 (EventBridge limit)
        for i in range(0, total_events, 10):
            batch = events[i:i+10]
            batch_number = (i // 10) + 1
            
            try:
                # Convert all events in batch to EventBridge format
                event_entries = [event.to_eventbridge_format() for event in batch]
                
                logger.debug(f"Processing batch {batch_number} with {len(event_entries)} events")
                
                batch_success_count = publish_events_batch_to_eventbridge(event_entries)
                successful_count += batch_success_count
                
                failed_count = len(batch) - batch_success_count
                
                if failed_count > 0:
                    logger.warning(f"Batch {batch_number}: {batch_success_count}/{len(batch)} events published successfully")
                else:
                    logger.debug(f"Batch {batch_number}: All {len(batch)} events published successfully")
                    
            except ValueError as e:
                logger.error(f"Validation error in batch {batch_number}: {str(e)}")
                
            except Exception as e:
                logger.error(f"Unexpected error in batch {batch_number}: {str(e)}")
        
        logger.info(f"Batch publishing complete: {successful_count}/{total_events} events published successfully")
        return successful_count
    
    def publish_event_with_retry(self, event: BaseEvent, max_retries: int = 3) -> bool:
        """
        Publish an event with exponential backoff retry logic.
        
        Args:
            event: The event to publish
            max_retries: Maximum number of retry attempts
            
        Returns:
            bool: True if successful, False if all retries failed
        """
        for attempt in range(max_retries + 1):
            try:
                success = self.publish_event(event)
                if success:
                    if attempt > 0:
                        logger.info(f"Event {event.event_id} published successfully on attempt {attempt + 1}")
                    return True
                
                # If this was the last attempt, don't wait
                if attempt == max_retries:
                    break
                
                # Exponential backoff: 2^attempt seconds (1, 2, 4, 8...)
                wait_time = 2 ** attempt
                logger.warning(f"Event {event.event_id} publish attempt {attempt + 1} failed, retrying in {wait_time}s")
                time.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1} for event {event.event_id}: {str(e)}")
                
                # If this was the last attempt, don't wait
                if attempt == max_retries:
                    break
                
                # Exponential backoff
                wait_time = 2 ** attempt
                logger.warning(f"Retrying event {event.event_id} in {wait_time}s")
                time.sleep(wait_time)
        
        logger.error(f"Failed to publish event {event.event_id} after {max_retries + 1} attempts")
        return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the event publishing system.
        
        Returns:
            Dict containing health check results
        """
        try:
            health_result = eventbridge_health_check()
            
            if health_result.get('status') == 'healthy':
                logger.debug("Event service health check passed")
            else:
                logger.warning(f"Event service health check failed: {health_result}")
            
            return health_result
            
        except Exception as e:
            logger.error(f"Error during event service health check: {str(e)}")
            return {
                'status': 'error',
                'error_message': str(e),
                'event_bus_name': self.event_bus_name
            }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

# Create a singleton instance that can be imported and used throughout the application
try:
    event_service = EventService()
    logger.info("Global EventService instance created successfully")
except Exception as e:
    logger.error(f"Failed to create global EventService instance: {str(e)}")
    # Create a mock service that logs errors but doesn't fail
    class MockEventService:
        def __init__(self):
            self.event_bus_name = "mock-event-bus"
            logger.warning("Using MockEventService - events will not be published")
        
        def publish_event(self, event: BaseEvent) -> bool:
            logger.warning(f"MockEventService: Would publish event {event.event_id} of type {event.event_type}")
            return True
        
        def publish_events_batch(self, events: List[BaseEvent]) -> int:
            logger.warning(f"MockEventService: Would publish {len(events)} events in batch")
            return len(events)
        
        def publish_event_with_retry(self, event: BaseEvent, max_retries: int = 3) -> bool:
            return self.publish_event(event)
        
        def health_check(self) -> Dict[str, Any]:
            return {
                'status': 'mock',
                'message': 'Using mock event service - EventBridge not available'
            }
    
    event_service = MockEventService()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def publish_event(event: BaseEvent) -> bool:
    """Convenience function to publish a single event using the global service"""
    return event_service.publish_event(event)

def publish_events_batch(events: List[BaseEvent]) -> int:
    """Convenience function to publish multiple events using the global service"""
    return event_service.publish_events_batch(events)

def publish_event_with_retry(event: BaseEvent, max_retries: int = 3) -> bool:
    """Convenience function to publish with retry using the global service"""
    return event_service.publish_event_with_retry(event, max_retries)

def event_service_health_check() -> Dict[str, Any]:
    """Convenience function to perform health check using the global service"""
    return event_service.health_check() 