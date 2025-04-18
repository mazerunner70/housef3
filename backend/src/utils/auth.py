"""
Authentication utility functions.
"""
import logging
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_user_from_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract user information from the event.
    
    Args:
        event: The Lambda event object containing the request context
        
    Returns:
        Dictionary containing user information if found, None otherwise
        The dictionary includes:
        - id: The user's unique identifier (sub)
        - email: The user's email address
        - auth_time: The time when the user was authenticated
    """
    try:
        request_context = event.get("requestContext", {})
        authorizer = request_context.get("authorizer", {}).get("jwt", {})
        claims = authorizer.get("claims", {})
        
        user_sub = claims.get("sub")
        if not user_sub:
            return None
        
        return {
            "id": user_sub,
            "email": claims.get("email", "unknown"),
            "auth_time": claims.get("auth_time")
        }
    except Exception as e:
        logger.error(f"Error extracting user from event: {str(e)}")
        return None 