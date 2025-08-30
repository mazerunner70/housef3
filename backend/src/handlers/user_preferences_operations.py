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
        return {
            "item": preferences.model_dump(by_alias=True, mode='json')
        }
    else:
        # Return default preferences structure if none exist
        default_preferences = {
            "userId": user_id,
            "preferences": {
                "transfers": {
                    "defaultDateRangeDays": 7,
                    "lastUsedDateRanges": [7, 14, 30],
                    "autoExpandSuggestion": True
                }
            },
            "createdAt": None,
            "updatedAt": None
        }
        logger.info(f"No preferences found for user: {user_id}, returning defaults")
        return {
            "item": default_preferences,
            "message": "Using default preferences"
        }


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
    return {
        "item": updated_preferences.model_dump(by_alias=True, mode='json'),
        "message": "Preferences updated successfully"
    }


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
    
    logger.info(f"Retrieved transfer preferences for user: {user_id}")
    return {
        "item": transfer_prefs
    }


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

    # Update transfer preferences
    service = UserPreferencesService()
    updated_preferences = asyncio.run(service.update_transfer_preferences(user_id, body))
    
    logger.info(f"Updated transfer preferences for user: {user_id}")
    return {
        "item": updated_preferences.model_dump(by_alias=True, mode='json'),
        "message": "Transfer preferences updated successfully"
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
    }
    
    handler_func = route_map.get(route)
    if not handler_func:
        raise ValueError(f"Unsupported route: {route}")
    
    return handler_func(event, user_id)