"""
Lambda handler for user preferences operations.
"""
import json
import logging
from typing import Dict, Any

from ..services.user_preferences_service import UserPreferencesService
from ..models.user_preferences import UserPreferencesCreate, UserPreferencesUpdate
from ..utils.lambda_utils import create_response, extract_user_id_from_event
from ..utils.auth import require_auth

# Configure logging
logger = logging.getLogger(__name__)


async def user_preferences_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler that routes user preferences requests to appropriate functions.
    """
    try:
        http_method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method')
        path = event.get('path') or event.get('rawPath', '')
        
        logger.info(f"User preferences handler called with method: {http_method}, path: {path}")
        
        # Route to appropriate handler based on method and path
        if path == '/user-preferences':
            if http_method == 'GET':
                return await get_user_preferences_handler(event, context)
            elif http_method == 'PUT':
                return await update_user_preferences_handler(event, context)
        elif path == '/user-preferences/transfers':
            if http_method == 'GET':
                return await get_transfer_preferences_handler(event, context)
            elif http_method == 'PUT':
                return await update_transfer_preferences_handler(event, context)
        
        # If no route matches
        logger.warning(f"No handler found for method: {http_method}, path: {path}")
        return create_response(404, {"error": "Not found"})
        
    except Exception as e:
        logger.error(f"Error in user_preferences_handler: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error"})


@require_auth
async def get_user_preferences_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Get user preferences.
    
    Args:
        event: Lambda event containing the request
        context: Lambda context
        
    Returns:
        API Gateway response with user preferences or error
    """
    try:
        # Extract user ID from the authenticated request
        user_id = extract_user_id_from_event(event)
        if not user_id:
            logger.warning("No user ID found in authenticated request")
            return create_response(400, {"error": "User ID is required"})

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
        return create_response(500, {"error": "Internal server error"})


@require_auth
async def update_user_preferences_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Update user preferences.
    
    Args:
        event: Lambda event containing the request
        context: Lambda context
        
    Returns:
        API Gateway response with updated preferences or error
    """
    try:
        # Extract user ID from the authenticated request
        user_id = extract_user_id_from_event(event)
        if not user_id:
            logger.warning("No user ID found in authenticated request")
            return create_response(400, {"error": "User ID is required"})

        # Parse request body
        if not event.get('body'):
            logger.warning("No request body provided")
            return create_response(400, {"error": "Request body is required"})

        try:
            body = json.loads(event['body'])
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in request body: {str(e)}")
            return create_response(400, {"error": "Invalid JSON in request body"})

        # Validate request data
        if 'preferences' not in body:
            logger.warning("No preferences provided in request body")
            return create_response(400, {"error": "Preferences are required"})

        # Create update DTO
        try:
            update_data = UserPreferencesUpdate(preferences=body['preferences'])
        except Exception as e:
            logger.warning(f"Invalid preferences data: {str(e)}")
            return create_response(400, {"error": f"Invalid preferences data: {str(e)}"})

        # Update preferences
        service = UserPreferencesService()
        updated_preferences = await service.update_user_preferences(user_id, update_data)
        
        logger.info(f"Updated preferences for user: {user_id}")
        return create_response(200, updated_preferences.model_dump(by_alias=True))

    except Exception as e:
        logger.error(f"Error in update_user_preferences_handler: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error"})


@require_auth
async def get_transfer_preferences_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Get transfer-specific preferences for a user.
    
    Args:
        event: Lambda event containing the request
        context: Lambda context
        
    Returns:
        API Gateway response with transfer preferences or error
    """
    try:
        # Extract user ID from the authenticated request
        user_id = extract_user_id_from_event(event)
        if not user_id:
            logger.warning("No user ID found in authenticated request")
            return create_response(400, {"error": "User ID is required"})

        # Get transfer preferences
        service = UserPreferencesService()
        transfer_prefs = await service.get_transfer_preferences(user_id)
        
        logger.info(f"Retrieved transfer preferences for user: {user_id}")
        return create_response(200, transfer_prefs)

    except Exception as e:
        logger.error(f"Error in get_transfer_preferences_handler: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error"})


@require_auth
async def update_transfer_preferences_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Update transfer-specific preferences for a user.
    
    Args:
        event: Lambda event containing the request
        context: Lambda context
        
    Returns:
        API Gateway response with updated preferences or error
    """
    try:
        # Extract user ID from the authenticated request
        user_id = extract_user_id_from_event(event)
        if not user_id:
            logger.warning("No user ID found in authenticated request")
            return create_response(400, {"error": "User ID is required"})

        # Parse request body
        if not event.get('body'):
            logger.warning("No request body provided")
            return create_response(400, {"error": "Request body is required"})

        try:
            body = json.loads(event['body'])
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in request body: {str(e)}")
            return create_response(400, {"error": "Invalid JSON in request body"})

        # Update transfer preferences
        service = UserPreferencesService()
        updated_preferences = await service.update_transfer_preferences(user_id, body)
        
        logger.info(f"Updated transfer preferences for user: {user_id}")
        return create_response(200, updated_preferences.model_dump(by_alias=True))

    except Exception as e:
        logger.error(f"Error in update_transfer_preferences_handler: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error"})
