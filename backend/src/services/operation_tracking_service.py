"""
Operation Tracking Service
Generic service for tracking long-running event-driven operations
"""

import os
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum

from utils.db.base import tables
from boto3.dynamodb.conditions import Attr
from pydantic import ValidationError
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class OperationStatus(str, Enum):
    """Standard operation statuses"""
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DENIED = "denied"


class OperationType(str, Enum):
    """Supported operation types"""
    FILE_DELETION = "file_deletion"
    FILE_UPLOAD = "file_upload"
    ACCOUNT_MODIFICATION = "account_modification"
    DATA_EXPORT = "data_export"
    BULK_CATEGORIZATION = "bulk_categorization"
    ACCOUNT_MIGRATION = "account_migration"
    RECURRING_CHARGE_DETECTION = "recurring_charge_detection"


class OperationTrackingService:
    """Generic service for tracking long-running operations"""
    
    def __init__(self):
        self.table = tables.workflows
        
        # Operation configurations
        self.operation_configs = {
            OperationType.FILE_DELETION: {
                'display_name': 'File Deletion',
                'estimated_duration_minutes': 3,
                'steps': [
                    {'name': 'initiated', 'description': 'Deletion request received'},
                    {'name': 'waiting_for_approval', 'description': 'Collecting approval votes'},
                    {'name': 'approved', 'description': 'All approvals received'},
                    {'name': 'executing', 'description': 'Deleting file and transactions'},
                    {'name': 'completed', 'description': 'File successfully deleted'}
                ],
                'cancellable_until': OperationStatus.APPROVED
            },
            OperationType.FILE_UPLOAD: {
                'display_name': 'File Upload',
                'estimated_duration_minutes': 5,
                'steps': [
                    {'name': 'initiated', 'description': 'Upload started'},
                    {'name': 'waiting_for_approval', 'description': 'Security and format validation'},
                    {'name': 'approved', 'description': 'Validation passed'},
                    {'name': 'executing', 'description': 'Processing transactions'},
                    {'name': 'completed', 'description': 'File processed successfully'}
                ],
                'cancellable_until': OperationStatus.EXECUTING
            },
            OperationType.DATA_EXPORT: {
                'display_name': 'Data Export',
                'estimated_duration_minutes': 10,
                'steps': [
                    {'name': 'initiated', 'description': 'Export request received'},
                    {'name': 'in_progress', 'description': 'Gathering data'},
                    {'name': 'executing', 'description': 'Generating export file'},
                    {'name': 'completed', 'description': 'Export ready for download'}
                ],
                'cancellable_until': OperationStatus.EXECUTING
            },
            OperationType.RECURRING_CHARGE_DETECTION: {
                'display_name': 'Recurring Charge Detection',
                'estimated_duration_minutes': 5,
                'steps': [
                    {'name': 'initiated', 'description': 'Detection request received'},
                    {'name': 'in_progress', 'description': 'Analyzing transaction patterns'},
                    {'name': 'executing', 'description': 'Saving detected patterns'},
                    {'name': 'completed', 'description': 'Pattern detection completed'}
                ],
                'cancellable_until': OperationStatus.IN_PROGRESS
            }
        }
    
    def start_operation(self, operation_type: OperationType, entity_id: str, 
                       user_id: str, context: Dict[str, Any], operation_id: Optional[str] = None) -> str:
        """Start tracking a new long-running operation"""
        try:
            # Use provided operation_id or generate a new one
            if operation_id is None:
                operation_id = f"op_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{entity_id[:8]}"
                logger.info(f"WORKFLOW_TABLE_UPDATE: Generated new operation ID - {operation_id}")
            else:
                logger.info(f"WORKFLOW_TABLE_UPDATE: Reusing existing operation ID - {operation_id}")
            
            config = self.operation_configs.get(operation_type, {})
            
            now_timestamp = int(datetime.now().timestamp() * 1000)  # Epoch milliseconds
            
            operation_record = {
                'operationId': operation_id,
                'operationType': operation_type.value,
                'entityId': entity_id,
                'userId': user_id,
                'status': OperationStatus.INITIATED.value,
                'progressPercentage': 0,
                'currentStep': 0,
                'totalSteps': len(config.get('steps', [])),
                'estimatedCompletion': self._calculate_estimated_completion(operation_type),
                'createdAt': now_timestamp,  # Epoch milliseconds (standard format)
                'updatedAt': now_timestamp,  # Epoch milliseconds (standard format)
                'ttl': int((datetime.now() + timedelta(days=7)).timestamp()),  # Keep for 7 days
                'context': context,
                'stepsCompleted': [],
                'currentStepDescription': 'File deletion request received',  # Set initial description
                'cancellable': True
                # Note: Don't set errorMessage to None - only set it when there's an actual error
            }
            
            self.table.put_item(Item=operation_record)
            
            logger.info(f"WORKFLOW_TABLE_UPDATE: Created new operation - operationId={operation_id}, type={operation_type.value}, entityId={entity_id}, userId={user_id}, status={OperationStatus.INITIATED.value}, progress=0%")
            logger.info(f"WORKFLOW_TABLE_UPDATE: Full record created: {operation_record}")
            return operation_id
            
        except (ValueError, ValidationError) as e:
            logger.exception(f"Validation error starting operation {operation_id}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error starting operation tracking: {e}")
            raise
    
    def update_operation_status(self, operation_id: str, status: OperationStatus, 
                              progress_percentage: Optional[int] = None,
                              current_step: Optional[int] = None,
                              step_description: Optional[str] = None,
                              error_message: Optional[str] = None,
                              additional_data: Optional[Dict[str, Any]] = None) -> None:
        """Update operation status and progress"""
        try:
            update_expression_parts = []
            expression_values = {}
            expression_names = {}
            
            # Always update status and timestamp
            update_expression_parts.append('#status = :status')
            update_expression_parts.append('updatedAt = :updated_at')
            expression_names['#status'] = 'status'
            expression_values[':status'] = status.value
            expression_values[':updated_at'] = int(datetime.now().timestamp() * 1000)  # Epoch milliseconds
            
            # Update progress if provided
            if progress_percentage is not None:
                update_expression_parts.append('progressPercentage = :progress')
                expression_values[':progress'] = progress_percentage
            
            # Update current step if provided
            if current_step is not None:
                update_expression_parts.append('currentStep = :step')
                expression_values[':step'] = current_step
            
            # Add step description if provided
            if step_description:
                update_expression_parts.append('currentStepDescription = :step_desc')
                expression_values[':step_desc'] = step_description
            
            # Add error message if provided
            if error_message:
                update_expression_parts.append('errorMessage = :error')
                expression_values[':error'] = error_message
            
            # Update cancellable status
            cancellable = self._is_cancellable(status)
            update_expression_parts.append('cancellable = :cancellable')
            expression_values[':cancellable'] = cancellable
            
            # Add additional data if provided (skip None values to avoid blanking fields)
            if additional_data:
                for key, value in additional_data.items():
                    if value is not None:  # Only update non-None values
                        safe_key = key.replace('.', '_').replace('-', '_')
                        update_expression_parts.append(f'{safe_key} = :{safe_key}')
                        expression_values[f':{safe_key}'] = value
            
            update_expression = 'SET ' + ', '.join(update_expression_parts)
            
            # Log the update before executing it
            logger.info(f"WORKFLOW_TABLE_UPDATE: Updating operation - operationId={operation_id}, status={status.value}, progress={progress_percentage}%, step={current_step}, description='{step_description}', error='{error_message}'")
            logger.info(f"WORKFLOW_TABLE_UPDATE: Update expression: {update_expression}")
            logger.info(f"WORKFLOW_TABLE_UPDATE: Expression values: {expression_values}")
            
            self.table.update_item(
                Key={
                    'operationId': operation_id
                },
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names if expression_names else None,
                ExpressionAttributeValues=expression_values
            )
            
            logger.info(f"WORKFLOW_TABLE_UPDATE: Successfully updated operation {operation_id}: {status.value} ({progress_percentage}%)")
            
        except (ValueError, ValidationError) as e:
            logger.exception(f"Validation error updating operation {operation_id}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error updating operation status {operation_id}: {e}")
            raise
    
    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get current operation status and progress"""
        try:
            logger.info(f"WORKFLOW_TABLE_QUERY: Getting operation status for operationId={operation_id}")
            
            response = self.table.get_item(
                Key={
                    'operationId': operation_id
                }
            )
            
            if 'Item' not in response:
                logger.warning(f"WORKFLOW_TABLE_QUERY: Operation not found - operationId={operation_id}")
                return None
            
            logger.info(f"WORKFLOW_TABLE_QUERY: Found operation - operationId={operation_id}, status={response['Item'].get('status')}, progress={response['Item'].get('progressPercentage')}%")
            
            operation = response['Item']
            
            # Validate required fields - fail fast if missing
            if 'operationType' not in operation:
                raise ValueError(f"Operation {operation_id} is missing required field 'operationType'")
            
            # Enrich with configuration data
            operation_type = OperationType(operation['operationType'])
            config = self.operation_configs.get(operation_type, {})
            
            # Calculate time remaining
            time_remaining = self._calculate_time_remaining(operation)
            
            # Convert DynamoDB Decimal objects back to appropriate types
            # DynamoDB stores integers as Decimals, but we want integers in API responses
            def convert_decimal_to_int(value, default=0):
                """Convert DynamoDB Decimal to int if it's a whole number, otherwise return default"""
                if value is None:
                    return default
                try:
                    from decimal import Decimal
                    if isinstance(value, Decimal):
                        # Check if it's a whole number
                        if value % 1 == 0:
                            return int(value)
                        else:
                            # It's a decimal with fractional part - shouldn't happen for these fields
                            logger.warning(f"Expected integer but got decimal: {value}")
                            return int(value)  # Truncate to integer
                    return int(value) if value is not None else default
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert value to int: {value}, using default: {default}")
                    return default

            def convert_decimal_to_int_timestamp(value):
                """Convert DynamoDB Decimal timestamp to int, preserving full precision"""
                if value is None:
                    return None
                try:
                    from decimal import Decimal
                    if isinstance(value, Decimal):
                        return int(value)
                    return int(value) if value is not None else None
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert timestamp to int: {value}")
                    return None

            return {
                'operationId': operation['operationId'],
                'operationType': operation['operationType'],
                'displayName': config.get('display_name', operation['operationType']),
                'entityId': operation['entityId'],
                'userId': operation['userId'],  # Required for authorization checks
                'status': operation['status'],
                'progressPercentage': convert_decimal_to_int(operation.get('progressPercentage'), 0),
                'currentStep': convert_decimal_to_int(operation.get('currentStep'), 0),
                'totalSteps': convert_decimal_to_int(operation.get('totalSteps'), 0),
                'currentStepDescription': operation.get('currentStepDescription'),
                'estimatedCompletion': convert_decimal_to_int_timestamp(operation.get('estimatedCompletion')),
                'timeRemaining': time_remaining,
                'createdAt': convert_decimal_to_int_timestamp(operation['createdAt']),
                'updatedAt': convert_decimal_to_int_timestamp(operation['updatedAt']),
                'errorMessage': operation.get('errorMessage'),
                'cancellable': operation.get('cancellable', False),
                'context': self._convert_context_decimals(operation.get('context', {})),
                'steps': config.get('steps', [])
            }
            
        except (ValueError, ValidationError) as e:
            logger.exception(f"Validation error getting operation status {operation_id}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error getting operation status {operation_id}: {e}")
            return None
    
    def list_user_operations(self, user_id: str, status_filter: Optional[List[OperationStatus]] = None,
                           operation_type_filter: Optional[List[OperationType]] = None,
                           limit: int = 50) -> List[Dict[str, Any]]:
        """List operations for a user with optional filters"""
        try:
            # Query operations for this user using the UserOperationsIndex
            from boto3.dynamodb.conditions import Key
            
            response = self.table.query(
                IndexName='UserOperationsIndex',
                KeyConditionExpression=Key('userId').eq(user_id),
                Limit=limit,
                ScanIndexForward=False  # Most recent first
            )
            
            operations = []
            for item in response.get('Items', []):
                operation_status = self.get_operation_status(item['operationId'])
                if operation_status:
                    # Apply filters
                    if status_filter and operation_status['status'] not in [s.value for s in status_filter]:
                        continue
                    if operation_type_filter and operation_status['operationType'] not in [t.value for t in operation_type_filter]:
                        continue
                    
                    operations.append(operation_status)
            
            return operations
            
        except (ValueError, ValidationError) as e:
            logger.exception(f"Validation error listing operations for user {user_id}: {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected error listing user operations for {user_id}: {e}")
            return []
    
    def cancel_operation(self, operation_id: str, user_id: str, reason: str = "Cancelled by user") -> bool:
        """Cancel an operation if it's still cancellable"""
        try:
            operation = self.get_operation_status(operation_id)
            if not operation:
                return False
            
            # Check if user owns this operation  
            # Check both the context userId and the top-level userId field
            context_user_id = operation.get('context', {}).get('userId')
            if context_user_id != user_id:
                logger.warning(f"User {user_id} attempted to cancel operation {operation_id} they don't own")
                return False
            
            # Check if operation is cancellable
            if not operation.get('cancellable', False):
                logger.warning(f"Operation {operation_id} is no longer cancellable")
                return False
            
            # Update to cancelled status
            self.update_operation_status(
                operation_id=operation_id,
                status=OperationStatus.CANCELLED,
                progress_percentage=0,
                error_message=reason
            )
            
            logger.info(f"Operation {operation_id} cancelled by user {user_id}: {reason}")
            return True
            
        except (ValueError, ValidationError) as e:
            logger.exception(f"Validation error cancelling operation {operation_id}: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error cancelling operation {operation_id}: {e}")
            return False
    
    def _calculate_estimated_completion(self, operation_type: OperationType) -> int:
        """Calculate estimated completion time in epoch milliseconds"""
        config = self.operation_configs.get(operation_type, {})
        duration_minutes = config.get('estimated_duration_minutes', 5)
        estimated_time = datetime.now() + timedelta(minutes=duration_minutes)
        return int(estimated_time.timestamp() * 1000)  # Epoch milliseconds
    
    def _calculate_time_remaining(self, operation: Dict[str, Any]) -> Optional[str]:
        """Calculate time remaining for operation"""
        try:
            if operation['status'] in [OperationStatus.COMPLETED.value, OperationStatus.FAILED.value, 
                                     OperationStatus.CANCELLED.value, OperationStatus.DENIED.value]:
                return None
            
            estimated_completion = operation.get('estimatedCompletion')
            if not estimated_completion:
                return None
            
            # Handle both epoch timestamp (new format) and ISO string (legacy format)
            if isinstance(estimated_completion, (int, float)):
                # Epoch timestamp in milliseconds
                completion_time = datetime.fromtimestamp(estimated_completion / 1000)
            else:
                # Legacy ISO format string
                completion_time = datetime.fromisoformat(estimated_completion.replace('Z', '+00:00'))
            
            now = datetime.now()
            
            if completion_time <= now:
                return "Completing soon..."
            
            remaining = completion_time - now
            minutes = int(remaining.total_seconds() / 60)
            
            if minutes < 1:
                return "Less than 1 minute"
            elif minutes == 1:
                return "1 minute"
            else:
                return f"{minutes} minutes"
                
        except Exception:
            return None
    
    def _is_cancellable(self, status: OperationStatus) -> bool:
        """Determine if operation is still cancellable"""
        non_cancellable_statuses = [
            OperationStatus.EXECUTING,
            OperationStatus.COMPLETED,
            OperationStatus.FAILED,
            OperationStatus.CANCELLED,
            OperationStatus.DENIED
        ]
        return status not in non_cancellable_statuses

    def _convert_context_decimals(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB Decimal objects in context to appropriate types"""
        if not context:
            return context
        
        converted_context = {}
        for key, value in context.items():
            if value is None:
                converted_context[key] = value
                continue
                
            try:
                from decimal import Decimal
                if isinstance(value, Decimal):
                    # For context fields that should be integers (like transactionCount, fileSize)
                    if key in ['transactionCount', 'fileSize', 'recordCount', 'itemCount']:
                        # Check if it's a whole number
                        if value % 1 == 0:
                            converted_context[key] = int(value)
                        else:
                            logger.warning(f"Expected integer for {key} but got decimal: {value}")
                            converted_context[key] = int(value)  # Truncate to integer
                    else:
                        # For other decimal fields, keep as string (like currency amounts)
                        converted_context[key] = str(value)
                else:
                    converted_context[key] = value
            except Exception as e:
                logger.warning(f"Error converting context field {key}: {e}")
                converted_context[key] = value
                
        return converted_context


# Global service instance
operation_tracking_service = OperationTrackingService()
