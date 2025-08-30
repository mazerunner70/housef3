"""
Handler decorators for reducing boilerplate code in Lambda handlers.

These decorators implement the patterns recommended in backend-conventions.mdc
to eliminate repetitive authentication, error handling, logging, and authorization code.
"""

import json
import logging
import traceback
import uuid
from datetime import datetime
from functools import wraps
from typing import Dict, Any, Callable, Optional, Union

from pydantic import ValidationError

from utils.auth import get_user_from_event, NotAuthorized, NotFound
from utils.lambda_utils import create_response
from utils.db_utils import (
    checked_mandatory_account,
    checked_mandatory_transaction,
    checked_mandatory_category,
    checked_mandatory_transaction_file,
    checked_mandatory_file_map,
)

logger = logging.getLogger(__name__)


def standard_error_handling(func: Callable) -> Callable:
    """
    Decorator that provides standard error handling for Lambda handlers.
    
    Maps common exceptions to appropriate HTTP status codes:
    - ValidationError, ValueError, KeyError -> 400 Bad Request
    - NotFound -> 404 Not Found  
    - NotAuthorized -> 403 Forbidden
    - Exception -> 500 Internal Server Error
    
    Handlers decorated with this can focus on business logic and return raw data.
    The decorator will wrap the result in a proper API Gateway response.
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Dict[str, Any]:
        try:
            result = func(*args, **kwargs)
            
            # If handler returns a dict with statusCode, it's already a response
            if isinstance(result, dict) and "statusCode" in result:
                return result
            
            # Otherwise, wrap in success response
            return create_response(200, result)
            
        except (ValidationError, ValueError, KeyError) as e:
            logger.error(f"Validation error in {func.__name__}: {str(e)}")
            return create_response(400, {"message": str(e)})
            
        except NotFound as e:
            logger.warning(f"Resource not found in {func.__name__}: {str(e)}")
            return create_response(404, {"message": str(e)})
            
        except NotAuthorized as e:
            logger.warning(f"Authorization error in {func.__name__}: {str(e)}")
            return create_response(403, {"message": str(e)})
            
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            logger.error(f"Stacktrace: {traceback.format_exc()}")
            return create_response(500, {"message": f"Error in {func.__name__.replace('_handler', '')}"})
    
    return wrapper


def handle_validation_errors(func: Callable) -> Callable:
    """Decorator that handles validation errors specifically."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Dict[str, Any]:
        try:
            return func(*args, **kwargs)
        except (ValidationError, ValueError, KeyError) as e:
            logger.error(f"Validation error in {func.__name__}: {str(e)}")
            return create_response(400, {"message": str(e)})
    return wrapper


def handle_not_found_errors(func: Callable) -> Callable:
    """Decorator that handles not found errors specifically."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Dict[str, Any]:
        try:
            return func(*args, **kwargs)
        except NotFound as e:
            logger.warning(f"Resource not found in {func.__name__}: {str(e)}")
            return create_response(404, {"message": str(e)})
    return wrapper


def handle_server_errors(func: Callable) -> Callable:
    """Decorator that handles unexpected server errors."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Dict[str, Any]:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            logger.error(f"Stacktrace: {traceback.format_exc()}")
            return create_response(500, {"message": f"Error in {func.__name__.replace('_handler', '')}"})
    return wrapper


def require_resource_ownership(resource_param: str, resource_type: str):
    """
    Decorator factory that verifies resource ownership with explicit resource type.
    
    Args:
        resource_param: The parameter name containing the resource ID (e.g., "account_id", "transaction_id")
        resource_type: The type of resource to verify ("account", "transaction", "category", "transaction_file", "file_map")
    
    The decorator will:
    1. Extract the resource ID from path parameters
    2. Verify the resource exists and belongs to the user
    3. Pass the resource object to the handler function
    
    Usage:
        @require_resource_ownership("account_id", "account")
        @require_resource_ownership("transaction_id", "transaction")
        @require_resource_ownership("category_id", "category")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(event: Dict[str, Any], user_id: str, *args, **kwargs) -> Dict[str, Any]:
            try:
                # Extract resource ID from path parameters
                path_params = event.get("pathParameters", {}) or {}
                resource_id = path_params.get(resource_param)
                
                if not resource_id:
                    raise ValueError(f"Path parameter '{resource_param}' is required")
                
                # Convert to UUID and verify ownership
                resource_uuid = uuid.UUID(resource_id)
                
                # Map resource types to their checker functions
                checker_map = {
                    "account": checked_mandatory_account,
                    "transaction": checked_mandatory_transaction,
                    "category": checked_mandatory_category,
                    "transaction_file": checked_mandatory_transaction_file,
                    "file_map": checked_mandatory_file_map,
                }
                
                checker = checker_map.get(resource_type)
                if not checker:
                    raise NotImplementedError(f"Resource ownership checking not implemented for resource type '{resource_type}'")
                
                # Verify resource ownership and get the resource object
                resource = checker(resource_uuid, user_id)
                
                # Call the original function with the verified resource
                return func(event, user_id, resource, *args, **kwargs)
                
            except ValueError as e:
                logger.error(f"Invalid resource ID in {func.__name__}: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Error verifying resource ownership in {func.__name__}: {str(e)}")
                raise
        
        return wrapper
    return decorator


def log_request_response(func: Callable) -> Callable:
    """
    Decorator that logs request and response details for debugging and monitoring.
    
    Logs:
    - Request ID, method, route
    - Request start/end time and duration
    - Response status code
    - Error details if any
    """
    @wraps(func)
    def wrapper(event: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        # Extract request context
        request_context = event.get("requestContext", {})
        request_id = request_context.get("requestId", "unknown")
        method = request_context.get("http", {}).get("method", "unknown")
        route = event.get("routeKey", "unknown")
        
        start_time = datetime.utcnow()
        logger.info(f"[{request_id}] {method} {route} - Request started")
        
        try:
            result = func(event, *args, **kwargs)
            
            # Log successful response
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            status_code = result.get("statusCode", "unknown") if isinstance(result, dict) else "unknown"
            logger.info(f"[{request_id}] {method} {route} - Response {status_code} in {duration_ms:.1f}ms")
            
            return result
            
        except Exception as e:
            # Log error response
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            logger.error(f"[{request_id}] {method} {route} - Error after {duration_ms:.1f}ms: {str(e)}")
            raise
    
    return wrapper


def require_authenticated_user(func: Callable) -> Callable:
    """
    Decorator that extracts and validates authenticated user from event.
    
    This is similar to @require_auth but designed to work with the new decorator patterns.
    It extracts the user and passes it as the second parameter to the handler.
    """
    @wraps(func)
    def wrapper(event: Dict[str, Any], context: Any, *args, **kwargs) -> Dict[str, Any]:
        # Extract user from event
        user = get_user_from_event(event)
        if not user:
            logger.warning("Authentication required but no user found in event")
            return create_response(401, {"message": "Unauthorized"})
        
        user_id = user["id"]
        
        # Call the original function with user_id as second parameter
        return func(event, user_id, *args, **kwargs)
    
    return wrapper


# Convenience decorator that combines common patterns
def api_handler(
    require_auth: bool = True,
    require_ownership: Optional[tuple] = None,
    log_requests: bool = True,
    handle_errors: bool = True
):
    """
    Convenience decorator factory that combines common handler patterns.
    
    Args:
        require_auth: Whether to require authentication
        require_ownership: Tuple of (resource_param, resource_type) for ownership verification
        log_requests: Whether to log request/response details
        handle_errors: Whether to handle errors automatically
    
    Example:
        @api_handler(require_ownership=("account_id", "account"))
        def update_account_handler(event, user_id, account):
            # Handler receives authenticated user_id and verified account
            return {"message": "success"}
            
        @api_handler(require_ownership=("transaction_id", "transaction"))
        def update_transaction_handler(event, user_id, transaction):
            # Handler receives authenticated user_id and verified transaction
            return {"message": "success"}
    """
    def decorator(func: Callable) -> Callable:
        decorated_func = func
        
        # Apply decorators in reverse order (innermost first)
        if handle_errors:
            decorated_func = standard_error_handling(decorated_func)
        
        if require_ownership:
            if not isinstance(require_ownership, tuple) or len(require_ownership) != 2:
                raise ValueError("require_ownership must be a tuple of (resource_param, resource_type)")
            resource_param, resource_type = require_ownership
            decorated_func = require_resource_ownership(resource_param, resource_type)(decorated_func)
        
        if require_auth:
            decorated_func = require_authenticated_user(decorated_func)
        
        if log_requests:
            decorated_func = log_request_response(decorated_func)
        
        return decorated_func
    
    return decorator
