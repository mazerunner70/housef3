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
from utils.lambda_utils import create_response, mandatory_path_parameter, handle_error
from utils.handler_decorators import api_handler, require_authenticated_user, standard_error_handling

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


@api_handler()
def get_workflow_status_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Get the status of a long-running workflow"""
    try:
        workflow_id = mandatory_path_parameter(event, 'workflowId')
        
        status = operation_tracking_service.get_operation_status(workflow_id)
        
        if not status:
            return create_response(404, {"message": "Workflow not found"})
        
        # Verify user owns this workflow
        if status.get('context', {}).get('userId') != user_id:
            return create_response(403, {"message": "Access denied"})
        
        return create_response(200, status)
        
    except ValueError as e:
        logger.error(f"Error getting workflow status: {str(e)}")
        return handle_error(400, str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_workflow_status_handler: {str(e)}", exc_info=True)
        return handle_error(500, "Internal server error")


@api_handler()
def list_user_workflows_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """List workflows for the current user"""
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        
        status_filter = None
        if query_params.get('status'):
            try:
                status_filter = [OperationStatus(s.strip()) for s in query_params['status'].split(',')]
            except ValueError as e:
                return create_response(400, {"message": f"Invalid status filter: {str(e)}"})
        
        workflow_type_filter = None
        if query_params.get('workflowType'):
            try:
                workflow_type_filter = [OperationType(t.strip()) for t in query_params['workflowType'].split(',')]
            except ValueError as e:
                return create_response(400, {"message": f"Invalid workflow type filter: {str(e)}"})
        
        limit = 50
        if query_params.get('limit'):
            try:
                limit = int(query_params['limit'])
                if limit < 1 or limit > 100:
                    return create_response(400, {"message": "Limit must be between 1 and 100"})
            except ValueError:
                return create_response(400, {"message": "Invalid limit parameter"})
        
        workflows = operation_tracking_service.list_user_operations(
            user_id=user_id,
            status_filter=status_filter,
            operation_type_filter=workflow_type_filter,
            limit=limit
        )
        
        return create_response(200, {"workflows": workflows})
        
    except Exception as e:
        logger.error(f"Unexpected error in list_user_workflows_handler: {str(e)}", exc_info=True)
        return handle_error(500, "Internal server error")


@api_handler()
def cancel_workflow_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Cancel a long-running workflow"""
    try:
        workflow_id = mandatory_path_parameter(event, 'workflowId')
        
        # Parse request body
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError:
                return create_response(400, {"message": "Invalid JSON in request body"})
        
        reason = body.get('reason', 'Cancelled by user')
        
        success = operation_tracking_service.cancel_operation(workflow_id, user_id, reason)
        
        if success:
            return create_response(200, {"message": "Workflow cancelled successfully"})
        else:
            return create_response(400, {"message": "Workflow could not be cancelled"})
        
    except ValueError as e:
        logger.error(f"Error cancelling workflow: {str(e)}")
        return handle_error(400, str(e))
    except Exception as e:
        logger.error(f"Unexpected error in cancel_workflow_handler: {str(e)}", exc_info=True)
        return handle_error(500, "Internal server error")


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
