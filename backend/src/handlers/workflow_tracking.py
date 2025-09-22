"""
Workflow Tracking Handler
Handles workflow tracking endpoints for all long-running, multi-step processes
"""

import json
import logging
from typing import Dict, Any

# Service imports
from services.operation_tracking_service import operation_tracking_service, OperationType, OperationStatus

# Utility imports
from utils.lambda_utils import create_response, mandatory_path_parameter, optional_query_parameter, handle_error
from utils.handler_decorators import api_handler, require_authenticated_user, standard_error_handling
from utils.db_utils import checked_mandatory_workflow

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


@api_handler()
def get_workflow_status_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Get the status of a long-running workflow"""
    workflow_id = mandatory_path_parameter(event, 'workflowId')
    workflow = checked_mandatory_workflow(workflow_id, user_id)
    
    return {
        "workflow": workflow,
        "metadata": {
            "workflowId": workflow_id,
            "requestedBy": user_id
        }
    }


@api_handler()
def list_user_workflows_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """List workflows for the current user"""
    # Parse optional query parameters
    status_filter = None
    status_str = optional_query_parameter(event, 'status')
    if status_str:
        try:
            status_values = [s.strip() for s in status_str.split(',') if s.strip()]
            status_filter = [OperationStatus(s) for s in status_values]
        except ValueError as e:
            raise ValueError(f"Invalid status filter: {str(e)}")
    
    workflow_type_filter = None
    type_str = optional_query_parameter(event, 'workflowType')
    if type_str:
        try:
            type_values = [t.strip() for t in type_str.split(',') if t.strip()]
            workflow_type_filter = [OperationType(t) for t in type_values]
        except ValueError as e:
            raise ValueError(f"Invalid workflow type filter: {str(e)}")
    
    # Parse limit with validation
    limit = 50  # Default value
    limit_str = optional_query_parameter(event, 'limit')
    if limit_str:
        try:
            limit = int(limit_str)
            if limit < 1 or limit > 100:
                raise ValueError("Limit must be between 1 and 100")
        except ValueError as e:
            if "invalid literal" in str(e).lower():
                raise ValueError(f"Limit must be a valid integer, got: {limit_str}")
            raise
    
    workflows = operation_tracking_service.list_user_operations(
        user_id=user_id,
        status_filter=status_filter,
        operation_type_filter=workflow_type_filter,
        limit=limit
    )
    
    return {
        "workflows": workflows,
        "metadata": {
            "totalWorkflows": len(workflows),
            "userId": user_id,
            "appliedFilters": {
                "status": [s.value for s in status_filter] if status_filter else None,
                "workflowType": [t.value for t in workflow_type_filter] if workflow_type_filter else None,
                "limit": limit
            }
        }
    }


@api_handler()
def cancel_workflow_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Cancel a long-running workflow"""
    workflow_id = mandatory_path_parameter(event, 'workflowId')
    
    # Verify workflow exists and user owns it
    checked_mandatory_workflow(workflow_id, user_id)
    
    # Parse and validate request body
    body = {}
    if event.get('body'):
        body_str = event['body'].strip()
        if not body_str:
            raise ValueError("Request body cannot be empty")
        try:
            body = json.loads(body_str)
            if not isinstance(body, dict):
                raise ValueError("Request body must be a JSON object")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in request body: {str(e)}")
    
    # Validate reason parameter
    reason = body.get('reason', 'Cancelled by user')
    if reason is not None:
        if not isinstance(reason, str):
            raise ValueError("Cancellation reason must be a string")
        reason = reason.strip()
        if len(reason) > 500:  # Reasonable limit for cancellation reasons
            raise ValueError("Cancellation reason cannot exceed 500 characters")
    
    success = operation_tracking_service.cancel_operation(workflow_id, user_id, reason)
    
    if success:
        return {
            "message": "Workflow cancelled successfully",
            "workflowId": workflow_id,
            "cancelledBy": user_id
        }
    else:
        raise ValueError("Workflow could not be cancelled - it may not exist, not be owned by you, or not be in a cancellable state")


@require_authenticated_user
@standard_error_handling  
def handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Main handler for workflow tracking endpoints."""
    route = event.get("routeKey")
    if not route:
        raise ValueError("Route not specified")
    
    route_map = {
        "GET /workflows/{workflowId}/status": get_workflow_status_handler,
        "GET /workflows": list_user_workflows_handler,
        "POST /workflows/{workflowId}/cancel": cancel_workflow_handler,
    }
    
    handler_func = route_map.get(route)
    if not handler_func:
        raise ValueError(f"Unsupported route: {route}")
    
    return handler_func(event, user_id)
