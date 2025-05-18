"""
Authentication utility functions.
"""
import logging
from typing import Dict, Any, Optional

from models.file_map import FieldMapping, FileMap
from models.transaction_file import TransactionFile
from models.account import Account
from utils.db_utils import get_account, get_file_map, get_transaction_file

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class NotAuthorized(Exception):
    """Raised when a user is not authorized to access a resource."""
    pass

class NotFound(Exception):
    """Raised when a requested resource is not found."""
    pass

def get_user_from_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract user information from the event.
    
    Args:
        event: The Lambda event object containing the request context
        
    Returns:
        Dictionary containing user information if found, None otherwise
        The dictionary includes:
        - id: The user's unique identifier (sub)
        - email: The user's email addresss
        - auth_time: The time when the user was authenticated
    """
    try:
        request_context = event.get("requestContext", {})
        logger.info(f"Request context: {request_context}")
        
        authorizer = request_context.get("authorizer", {})
        logger.info(f"Authorizer: {authorizer}")
        
        # Get claims from authorizer.jwt.claims
        claims = authorizer.get("jwt", {}).get("claims", {})
        logger.info(f"Claims: {claims}")
        
        user_sub = claims.get("sub") 
        logger.info(f"User sub: {user_sub}")
        
        if not user_sub:
            logger.warning(f"No sub claim found in authorizer claims: {claims}")
            return None
        
        user_info = {
            "id": user_sub,
            "email": claims.get("email", "unknown"),
            "auth_time": claims.get("auth_time")
        }
        logger.info(f"Returning user info: {user_info}")
        return user_info
    except Exception as e:
        logger.error(f"Error extracting user from event: {str(e)}")
        return None

