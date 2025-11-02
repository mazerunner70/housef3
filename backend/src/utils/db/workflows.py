"""
Workflow database operations.

This module provides operations for workflow verification and authorization.
Note: Workflows use the operation_tracking_service, not direct DynamoDB access.
"""

import logging
from typing import Dict, Any

from .base import NotFound, NotAuthorized

logger = logging.getLogger(__name__)


def checked_mandatory_workflow(workflow_id: str, user_id: str) -> Dict[str, Any]:
    """
    Check if workflow exists and user has access to it.
    
    Args:
        workflow_id: ID of the workflow to check
        user_id: ID of the user requesting access
        
    Returns:
        Workflow status dictionary
        
    Raises:
        ValueError: If workflow_id is invalid
        NotFound: If workflow doesn't exist
        NotAuthorized: If user doesn't own the workflow
    """
    from services.operation_tracking_service import operation_tracking_service
    
    if not workflow_id or not isinstance(workflow_id, str):
        raise ValueError("Invalid workflow ID format")
        
    status = operation_tracking_service.get_operation_status(workflow_id)
    if not status:
        raise NotFound("Workflow not found")
        
    # Debug logging to diagnose authorization issue
    workflow_user_id = status.get('userId')
    logger.info(f"WORKFLOW_AUTH_DEBUG: workflow_id={workflow_id}, request_user_id={user_id}")
    logger.info(f"WORKFLOW_AUTH_DEBUG: workflow_user_id from status={workflow_user_id}")
    logger.info(f"WORKFLOW_AUTH_DEBUG: status keys={list(status.keys())}")
    logger.info(f"WORKFLOW_AUTH_DEBUG: comparison result: workflow_user_id != user_id = {workflow_user_id != user_id}")
    
    if workflow_user_id != user_id:
        logger.error(f"WORKFLOW_AUTH_DEBUG: Authorization failed - workflow_user_id='{workflow_user_id}' != request_user_id='{user_id}'")
        raise NotAuthorized("Not authorized to access this workflow")
        
    return status

