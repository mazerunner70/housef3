"""
Authentication utility functions.
"""
import logging
from typing import Dict, Any, Optional

from models.field_map import FieldMapping
from models.transaction_file import TransactionFile
from models.account import Account
from utils.db_utils import get_account, get_field_mapping, get_transaction_file

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

class NotFound(Exception): pass
class NotAuthorized(Exception): pass
    
def checked_optional_file(file_id: str, user_id: str) -> Optional[TransactionFile]:
    if not file_id:
        return None
    file = get_transaction_file(file_id)
    if file.user_id != user_id:
        raise NotAuthorized("Not authorized to access this file")
    return file

def checked_mandatory_file(file_id: str, user_id: str) -> 'TransactionFile':
    file = checked_optional_file(file_id, user_id)
    if not file:
        raise NotFound("File not found")
    return file

def checked_mandatory_account(account_id: str, user_id: str) -> 'Account':
    account = checked_optional_account(account_id, user_id)
    if not account:
        raise NotFound("Account not found")
    return account

def checked_optional_account(account_id: str, user_id: str) -> Optional['Account']:
    if not account_id:
        return None
    account = get_account(account_id)
    if not account:
        return None
    if account.user_id != user_id:
        raise NotAuthorized("Not authorized to access this account")
    return account

def checked_optional_field_mapping(field_mapping_id: str, user_id: str) -> Optional['FieldMapping']:
    if not field_mapping_id:
        return None
    field_mapping = get_field_mapping(field_mapping_id)
    if not field_mapping:
        return None
    if field_mapping.user_id != user_id:
        raise NotAuthorized("Not authorized to access this field mapping")
    return field_mapping

def checked_mandatory_field_mapping(field_mapping_id: str, user_id: str) -> 'FieldMapping':
    field_mapping = checked_optional_field_mapping(field_mapping_id, user_id)
    if not field_mapping:
        raise NotFound("Field mapping not found")
    return field_mapping
