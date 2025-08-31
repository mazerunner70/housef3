"""
Lambda handler for user preferences operations.
"""
import asyncio
import json
import logging
from typing import Dict, Any

from services.user_preferences_service import UserPreferencesService
from models.user_preferences import UserPreferencesCreate, UserPreferencesUpdate
from utils.lambda_utils import parse_and_validate_json
from utils.handler_decorators import api_handler, require_authenticated_user, standard_error_handling

# Configure logging
logger = logging.getLogger(__name__)


@api_handler()
def get_user_preferences_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Get user preferences.
    
    Args:
        event: Lambda event containing the request
        user_id: Authenticated user ID (provided by decorator)
        
    Returns:
        User preferences or default preferences
    """
    # Get user preferences
    service = UserPreferencesService()
    preferences = asyncio.run(service.get_user_preferences(user_id))
    
    if preferences:
        logger.info(f"Retrieved preferences for user: {user_id}")
        return preferences.model_dump(by_alias=True, mode='json')
    else:
        # Return default preferences structure if none exist
        default_preferences = {
            "userId": user_id,
            "preferences": {
                "transfers": {
                    "defaultDateRangeDays": 7,
                    "lastUsedDateRanges": [7, 14, 30],
                    "autoExpandSuggestion": True,
                    "checkedDateRangeStart": None,
                    "checkedDateRangeEnd": None
                }
            },
            "createdAt": None,
            "updatedAt": None
        }
        logger.info(f"No preferences found for user: {user_id}, returning defaults")
        return default_preferences


@api_handler()
def update_user_preferences_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Update user preferences.
    
    Args:
        event: Lambda event containing the request
        user_id: Authenticated user ID (provided by decorator)
        
    Returns:
        Updated preferences
    """
    # Parse and validate request body
    update_data, error = parse_and_validate_json(event, UserPreferencesUpdate)
    if error:
        raise ValueError(error["message"])
    
    # Validate that update_data was successfully parsed
    if update_data is None:
        raise ValueError("Failed to parse request body: update data is None")

    # Update preferences
    service = UserPreferencesService()
    updated_preferences = asyncio.run(service.update_user_preferences(user_id, update_data))
    
    logger.info(f"Updated preferences for user: {user_id}")
    return updated_preferences.model_dump(by_alias=True, mode='json')


@api_handler()
def get_transfer_preferences_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Get transfer-specific preferences for a user.
    
    Args:
        event: Lambda event containing the request
        user_id: Authenticated user ID (provided by decorator)
        
    Returns:
        Transfer preferences
    """
    # Get transfer preferences
    service = UserPreferencesService()
    transfer_prefs = asyncio.run(service.get_transfer_preferences(user_id))
    logger.info(f"Transfer preferences: {transfer_prefs}")
    # Ensure timestamp fields are returned as integers, not strings
    for field in ['checkedDateRangeStart', 'checkedDateRangeEnd']:
        if transfer_prefs[field] is not None:
            try:
                transfer_prefs[field] = int(transfer_prefs[field])
                logger.warning(f"Converted string timestamp {field} to int for user {user_id}")
            except (ValueError, TypeError):
                logger.error(f"Invalid timestamp string for {field}: {transfer_prefs[field]} (user: {user_id})")
                transfer_prefs[field] = None
        else:
            logger.warning(f"No timestamp {field} found for user {user_id}")
    
    logger.info(f"Retrieved transfer preferences for user: {user_id}")
    return transfer_prefs


@api_handler()
def update_transfer_preferences_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Update transfer-specific preferences for a user.
    
    Args:
        event: Lambda event containing the request
        user_id: Authenticated user ID (provided by decorator)
        
    Returns:
        Updated transfer preferences
    """
    # Parse request body - transfer preferences use raw dict format
    if not event.get('body'):
        raise ValueError("Request body is required")

    try:
        body = json.loads(event['body'])
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in request body")

    # Ensure timestamp fields are integers, not strings
    for field in ['checkedDateRangeStart', 'checkedDateRangeEnd']:
        if field in body and body[field] is not None:
            if isinstance(body[field], str):
                try:
                    body[field] = int(body[field])
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid timestamp value for {field}: {body[field]}")
            elif not isinstance(body[field], int):
                raise ValueError(f"Timestamp field {field} must be an integer, got {type(body[field])}")

    # Update transfer preferences
    service = UserPreferencesService()
    updated_preferences = asyncio.run(service.update_transfer_preferences(user_id, body))
    
    logger.info(f"Updated transfer preferences for user: {user_id}")
    return updated_preferences.model_dump(by_alias=True, mode='json')


@api_handler()
def get_account_date_range_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Get the overall account date range for transfer checking.
    
    Args:
        event: Lambda event containing the request
        user_id: Authenticated user ID (provided by decorator)
        
    Returns:
        Account date range information
    """
    # Get account date range for transfers (in milliseconds)
    service = UserPreferencesService()
    earliest_ms, latest_ms = asyncio.run(service.get_account_date_range_for_transfers(user_id))
    
    logger.info(f"Retrieved account date range for user: {user_id}")
    return {
        "startDate": earliest_ms,
        "endDate": latest_ms
    }


@require_authenticated_user
@standard_error_handling
def handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Main handler for user preferences operations."""
    route = event.get("routeKey")
    if not route:
        raise ValueError("Route not specified")

    # Route to appropriate handler
    route_map = {
        "GET /user-preferences": get_user_preferences_handler,
        "PUT /user-preferences": update_user_preferences_handler,
        "GET /user-preferences/transfers": get_transfer_preferences_handler,
        "PUT /user-preferences/transfers": update_transfer_preferences_handler,
        "GET /user-preferences/account-date-range": get_account_date_range_handler,
    }
    
    handler_func = route_map.get(route)
    if not handler_func:
        raise ValueError(f"Unsupported route: {route}")
    
    return handler_func(event, user_id)