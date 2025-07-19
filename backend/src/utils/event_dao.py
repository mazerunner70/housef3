"""
Event Data Access Object for handling EventBridge operations.
"""
import logging
import os
import boto3
from typing import List, Optional, Dict, Any
from botocore.exceptions import ClientError, BotoCoreError
import json

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_eventbridge_client():
    """Get EventBridge client with region configuration"""
    return boto3.client('events', region_name=os.environ.get('AWS_REGION', 'eu-west-2'))

def get_event_bus_name() -> str:
    """Get the event bus name from environment variables"""
    # Try different possible environment variable names
    event_bus_name = (
        os.environ.get('EVENT_BUS_NAME') or 
        os.environ.get('EVENTBRIDGE_BUS_NAME') or
        f"housef3-{os.environ.get('ENVIRONMENT', 'dev')}-events"
    )
    return event_bus_name

def publish_event_to_eventbridge(event_entry: Dict[str, Any]) -> bool:
    """
    Publish a single event to EventBridge.
    
    Args:
        event_entry: The EventBridge-formatted event entry
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        client = get_eventbridge_client()
        event_bus_name = get_event_bus_name()
        
        # Add event bus name to entry
        eventbridge_entry = {
            **event_entry,
            'EventBusName': event_bus_name
        }
        
        logger.debug(f"Publishing event to EventBridge: {eventbridge_entry.get('Source', 'unknown')} - {eventbridge_entry.get('DetailType', 'unknown')}")
        
        response = client.put_events(Entries=[eventbridge_entry])
        
        # Check for failures
        if response.get('FailedEntryCount', 0) > 0:
            failed_entries = [
                entry for entry in response.get('Entries', [])
                if entry.get('ErrorCode')
            ]
            logger.error(f"Failed to publish event: {failed_entries}")
            return False
        
        logger.debug(f"Successfully published event to EventBridge")
        return True
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'UnknownError')
        error_message = e.response.get('Error', {}).get('Message', 'Unknown error message')
        logger.error(f"AWS ClientError publishing event: {error_code} - {error_message}")
        return False
        
    except BotoCoreError as e:
        logger.error(f"BotoCoreError publishing event: {str(e)}")
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error publishing event: {str(e)}")
        return False

def publish_events_batch_to_eventbridge(event_entries: List[Dict[str, Any]]) -> int:
    """
    Publish multiple events to EventBridge in a single batch.
    EventBridge supports up to 10 events per batch.
    
    Args:
        event_entries: List of EventBridge-formatted event entries
        
    Returns:
        int: Number of events successfully published
    """
    if not event_entries:
        return 0
    
    if len(event_entries) > 10:
        raise ValueError("EventBridge batch size cannot exceed 10 events")
    
    try:
        client = get_eventbridge_client()
        event_bus_name = get_event_bus_name()
        
        # Add event bus name to all entries
        entries_with_bus = [
            {**entry, 'EventBusName': event_bus_name}
            for entry in event_entries
        ]
        
        logger.debug(f"Publishing batch of {len(entries_with_bus)} events to EventBridge")
        
        response = client.put_events(Entries=entries_with_bus)
        
        failed_count = response.get('FailedEntryCount', 0)
        success_count = len(entries_with_bus) - failed_count
        
        if failed_count > 0:
            logger.warning(f"Batch publish: {success_count}/{len(entries_with_bus)} events published successfully")
            
            # Log details about failed entries
            for idx, entry_result in enumerate(response.get('Entries', [])):
                if entry_result.get('ErrorCode'):
                    logger.error(
                        f"Failed to publish event {idx}: "
                        f"{entry_result.get('ErrorCode')} - {entry_result.get('ErrorMessage')}"
                    )
        else:
            logger.debug(f"Batch publish: All {len(entries_with_bus)} events published successfully")
        
        return success_count
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'UnknownError')
        error_message = e.response.get('Error', {}).get('Message', 'Unknown error message')
        logger.error(f"AWS ClientError in batch publish: {error_code} - {error_message}")
        return 0
        
    except BotoCoreError as e:
        logger.error(f"BotoCoreError in batch publish: {str(e)}")
        return 0
        
    except Exception as e:
        logger.error(f"Unexpected error in batch publish: {str(e)}")
        return 0

def eventbridge_health_check() -> Dict[str, Any]:
    """
    Perform a health check on EventBridge connectivity.
    
    Returns:
        Dict containing health check results
    """
    try:
        client = get_eventbridge_client()
        event_bus_name = get_event_bus_name()
        
        # Try to describe the event bus to verify connectivity
        response = client.describe_event_bus(Name=event_bus_name)
        
        return {
            'status': 'healthy',
            'event_bus_name': event_bus_name,
            'event_bus_arn': response.get('Arn'),
            'region': os.environ.get('AWS_REGION', 'eu-west-2')
        }
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'UnknownError')
        error_message = e.response.get('Error', {}).get('Message', 'Unknown error message')
        return {
            'status': 'error',
            'error_code': error_code,
            'error_message': error_message,
            'event_bus_name': get_event_bus_name()
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error_message': str(e),
            'event_bus_name': get_event_bus_name()
        } 