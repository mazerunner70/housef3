"""
Audit Event Consumer Lambda

This Lambda function consumes ALL events from EventBridge and stores them in the 
event store DynamoDB table for auditing, compliance, and debugging purposes.

This consumer provides:
- Complete audit trail of all system events
- Event replay capability for debugging
- Compliance logging for regulatory requirements
- Event analytics and monitoring data
"""

import json
import logging
import os
import traceback
from typing import Dict, Any, Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
from consumers.base_consumer import BaseEventConsumer
from models.events import BaseEvent
import boto3


class AuditEventConsumer(BaseEventConsumer):
    """Consumer that audits all events by storing them in the event store"""
    
    def __init__(self):
        super().__init__("audit_consumer")
        self._lambda_request_id: Optional[str] = None
    
    def should_process_event(self, event: BaseEvent) -> bool:
        """Process ALL events for auditing purposes"""
        return True  # Audit everything
    
    def process_event(self, event: BaseEvent) -> None:
        """Store the event in the audit/event store"""
        try:
            logger.info(f"Auditing event {event.event_id} of type {event.event_type}")
            
            # Create audit record with additional metadata
            audit_record = self._create_audit_record(event)
            
            # Store in event store using DynamoDB
            success = self._store_audit_record(audit_record)
            
            if success:
                logger.info(f"Successfully audited event {event.event_id}")
                self._log_audit_metrics(event, success=True)
            else:
                logger.error(f"Failed to audit event {event.event_id}")
                self._log_audit_metrics(event, success=False)
                raise Exception("Failed to store audit record")
                
        except Exception as e:
            logger.error(f"Error auditing event {event.event_id}: {str(e)}")
            logger.error(f"Stacktrace: {traceback.format_exc()}")
            self._log_audit_metrics(event, success=False, error=str(e))
            raise
    
    def _create_audit_record(self, event: BaseEvent) -> Dict[str, Any]:
        """Create comprehensive audit record from event"""
        try:
            audit_record = {
                # Event identification
                'eventId': event.event_id,
                'eventType': event.event_type,
                'eventVersion': event.event_version,
                'source': event.source,
                
                # Timing information
                'originalTimestamp': event.timestamp,
                'auditTimestamp': int(datetime.now().timestamp() * 1000),
                
                # User and context
                'userId': event.user_id,
                'correlationId': getattr(event, 'correlation_id', None),
                'causationId': getattr(event, 'causation_id', None),
                
                # Event data (full payload)
                'eventData': event.data or {},
                'eventMetadata': getattr(event, 'metadata', {}),
                
                # Audit metadata
                'auditVersion': '1.0',
                'processingStatus': 'success',  # Will be updated if processing fails
                'consumerInfo': {
                    'consumerName': self.consumer_name,
                    'lambdaRequestId': getattr(self, '_lambda_request_id', None),
                    'lambdaFunction': os.environ.get('AWS_LAMBDA_FUNCTION_NAME'),
                    'lambdaVersion': os.environ.get('AWS_LAMBDA_FUNCTION_VERSION')
                }
            }
            
            return audit_record
            
        except Exception as e:
            logger.error(f"Error creating audit record: {str(e)}")
            # Return minimal audit record in case of error
            return {
                'eventId': getattr(event, 'event_id', 'unknown'),
                'eventType': getattr(event, 'event_type', 'unknown'),
                'auditTimestamp': int(datetime.now().timestamp() * 1000),
                'processingStatus': 'error',
                'errorMessage': str(e)
            }
    
    def _store_audit_record(self, audit_record: Dict[str, Any]) -> bool:
        """Store audit record in DynamoDB event store"""
        try:
            # Get event store table name from environment
            event_store_table_name = os.environ.get('EVENT_STORE_TABLE', 'housef3-dev-event-store')
            
            # Initialize DynamoDB table
            dynamodb = boto3.resource('dynamodb')
            table = dynamodb.Table(event_store_table_name)
            
            # Store the audit record
            table.put_item(Item=audit_record)
            return True
            
        except Exception as e:
            logger.error(f"Failed to store audit record: {str(e)}")
            return False
    
    def _log_audit_metrics(self, event: BaseEvent, success: bool, error: Optional[str] = None):
        """Log metrics for audit monitoring"""
        try:
            metrics = {
                'event_type': event.event_type,
                'event_id': event.event_id,
                'user_id': event.user_id,
                'audit_success': success,
                'audit_timestamp': int(datetime.now().timestamp() * 1000),
                'error_message': error
            }
            
            # Log as structured JSON for CloudWatch insights
            logger.info(f"AUDIT_METRICS: {json.dumps(metrics)}")
            
        except Exception as e:
            logger.warning(f"Failed to log audit metrics: {str(e)}")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for audit events from EventBridge.
    
    This handler audits ALL events regardless of type.
    
    Expected event format from EventBridge:
    {
        "version": "0",
        "id": "event-id",
        "detail-type": "Application Event",
        "source": "transaction.service",
        "detail": {
            "eventId": "...",
            "eventType": "...",
            "userId": "...",
            "data": { ... }
        }
    }
    """
    try:
        logger.info(f"Audit consumer received event for auditing")
        
        # Store Lambda request ID for audit trail
        consumer = AuditEventConsumer()
        consumer._lambda_request_id = context.aws_request_id if context else None
        
        result = consumer.handle_eventbridge_event(event, context)
        
        logger.info(f"Audit consumer completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Audit consumer failed: {str(e)}")
        logger.error(f"Event: {json.dumps(event, default=str)}")  # Use default=str for non-serializable objects
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        
        # For audit consumer, we want to return success even if auditing fails
        # to prevent blocking the original event processing
        logger.warning("Audit consumer failed but returning success to prevent blocking event flow")
        return {
            'statusCode': 200,  # Return success to prevent EventBridge retries
            'body': json.dumps({
                'warning': 'Audit consumer failed but event flow not blocked',
                'error': str(e)
            })
        } 