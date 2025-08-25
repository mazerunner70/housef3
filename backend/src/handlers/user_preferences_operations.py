"""
Lambda handler for user preferences operations.
"""
import asyncio
import json
import logging
import traceback
from typing import Dict, Any

from services.user_preferences_service import UserPreferencesService
from models.user_preferences import UserPreferencesCreate, UserPreferencesUpdate
from utils.lambda_utils import create_response
from utils.auth import get_user_from_event


# Configure logging
logger = logging.getLogger(__name__)


async def user_preferences_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler that routes user preferences requests to appropriate functions.
    """
    try:
        # Get user from Cognito
        user = get_user_from_event(event)
        if not user:
            return create_response(401, {"message": "Unauthorized"})
        user_id = user["id"]
        
        # Get route from event
        route = event.get("routeKey")
        if not route:
            # Fallback to path-based routing for backwards compatibility
            http_method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method')
            path = event.get('path') or event.get('rawPath', '')
            logger.info(f"Using path-based routing - method: {http_method}, path: {path}")
            
            if path == '/user-preferences':
                if http_method == 'GET':
                    return await get_user_preferences_handler(event, user_id)
                elif http_method == 'PUT':
                    return await update_user_preferences_handler(event, user_id)
            elif path == '/user-preferences/transfers':
                if http_method == 'GET':
                    return await get_transfer_preferences_handler(event, user_id)
                elif http_method == 'PUT':
                    return await update_transfer_preferences_handler(event, user_id)
            
            logger.warning(f"No handler found for method: {http_method}, path: {path}")
            return create_response(404, {"message": "Not found"})
        
        logger.info(f"Request: {route}")
        
        # Route to appropriate handler using route key
        if route == "GET /user-preferences":
            return await get_user_preferences_handler(event, user_id)
        elif route == "PUT /user-preferences":
            return await update_user_preferences_handler(event, user_id)
        elif route == "GET /user-preferences/transfers":
            return await get_transfer_preferences_handler(event, user_id)
        elif route == "PUT /user-preferences/transfers":
            return await update_transfer_preferences_handler(event, user_id)
        else:
            return create_response(400, {"message": f"Unsupported route: {route}"})
        
    except Exception as e:
        logger.error(f"Error in user_preferences_handler: {str(e)}", exc_info=True)
        return create_response(500, {"message": "Internal server error"})


async def get_user_preferences_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Get user preferences.
    
    Args:
        event: Lambda event containing the request
        user_id: Authenticated user ID
        
    Returns:
        API Gateway response with user preferences or error
    """
    try:

        # Get user preferences
        service = UserPreferencesService()
        preferences = await service.get_user_preferences(user_id)
        
        if preferences:
            logger.info(f"Retrieved preferences for user: {user_id}")
            return create_response(200, preferences.model_dump(by_alias=True))
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
            return create_response(200, default_preferences)

    except Exception as e:
        logger.error(f"Error in get_user_preferences_handler: {str(e)}", exc_info=True)
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"message": "Internal server error"})


async def update_user_preferences_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Update user preferences.
    
    Args:
        event: Lambda event containing the request
        user_id: Authenticated user ID
        
    Returns:
        API Gateway response with updated preferences or error
    """
    try:
        # Parse request body
        if not event.get('body'):
            logger.warning("No request body provided")
            return create_response(400, {"message": "Request body is required"})

        try:
            body = json.loads(event['body'])
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in request body: {str(e)}")
            return create_response(400, {"message": "Invalid JSON in request body"})

        # Validate request data
        if 'preferences' not in body:
            logger.warning("No preferences provided in request body")
            return create_response(400, {"message": "Preferences are required"})

        # Create update DTO
        try:
            update_data = UserPreferencesUpdate(preferences=body['preferences'])
        except Exception as e:
            logger.warning(f"Invalid preferences data: {str(e)}")
            return create_response(400, {"message": f"Invalid preferences data: {str(e)}"})

        # Update preferences
        service = UserPreferencesService()
        updated_preferences = await service.update_user_preferences(user_id, update_data)
        
        logger.info(f"Updated preferences for user: {user_id}")
        return create_response(200, updated_preferences.model_dump(by_alias=True))

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(400, {"message": str(e)})
    except Exception as e:
        logger.error(f"Error in update_user_preferences_handler: {str(e)}", exc_info=True)
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"message": "Internal server error"})


async def get_transfer_preferences_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Get transfer-specific preferences for a user.
    
    Args:
        event: Lambda event containing the request
        user_id: Authenticated user ID
        
    Returns:
        API Gateway response with transfer preferences or error
    """
    try:
        # Get transfer preferences
        service = UserPreferencesService()
        transfer_prefs = await service.get_transfer_preferences(user_id)
        
        logger.info(f"Retrieved transfer preferences for user: {user_id}")
        return create_response(200, transfer_prefs)

    except Exception as e:
        logger.error(f"Error in get_transfer_preferences_handler: {str(e)}", exc_info=True)
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"message": "Internal server error"})


async def update_transfer_preferences_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Update transfer-specific preferences for a user.
    
    Args:
        event: Lambda event containing the request
        user_id: Authenticated user ID
        
    Returns:
        API Gateway response with updated preferences or error
    """
    try:
        # Parse request body
        if not event.get('body'):
            logger.warning("No request body provided")
            return create_response(400, {"message": "Request body is required"})

        try:
            body = json.loads(event['body'])
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in request body: {str(e)}")
            return create_response(400, {"message": "Invalid JSON in request body"})

        # Update transfer preferences
        service = UserPreferencesService()
        updated_preferences = await service.update_transfer_preferences(user_id, body)
        
        logger.info(f"Updated transfer preferences for user: {user_id}")
        return create_response(200, updated_preferences.model_dump(by_alias=True))

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(400, {"message": str(e)})
    except Exception as e:
        logger.error(f"Error in update_transfer_preferences_handler: {str(e)}", exc_info=True)
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"message": "Internal server error"})


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main handler for user preferences operations."""
    try:
        # Get user from Cognito
        user = get_user_from_event(event)
        if not user:
            return create_response(401, {"message": "Unauthorized"})
        user_id = user["id"]
        
        # Get route from event
        route = event.get("routeKey")
        if not route:
            # Fallback to async handler for backwards compatibility
            return asyncio.run(user_preferences_handler(event, context))
        
        logger.info(f"Request: {route}")
        
        # Route to appropriate handler using route key
        if route == "GET /user-preferences":
            return asyncio.run(get_user_preferences_handler(event, user_id))
        elif route == "PUT /user-preferences":
            return asyncio.run(update_user_preferences_handler(event, user_id))
        elif route == "GET /user-preferences/transfers":
            return asyncio.run(get_transfer_preferences_handler(event, user_id))
        elif route == "PUT /user-preferences/transfers":
            return asyncio.run(update_transfer_preferences_handler(event, user_id))
        else:
            return create_response(400, {"message": f"Unsupported route: {route}"})
    except Exception as e:
        logger.error(f"Error in user preferences handler: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"message": "Internal server error"})
