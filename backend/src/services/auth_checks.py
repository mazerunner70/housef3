"""
Authorization check functions.
"""
from typing import Optional
import uuid

from models.account import Account
from models.file_map import FileMap
from models.transaction_file import TransactionFile
from utils.db_utils import (
    get_file_map,
    get_transaction_file,
    get_account,
    checked_mandatory_file_map  # Import from db_utils
)
from utils.auth import NotAuthorized, NotFound

def checked_mandatory_account(account_id: Optional[uuid.UUID], user_id: str) -> Account:
    """
    Check if an account exists and the user has access to it.
    
    Args:
        account_id: ID of the account to check
        user_id: ID of the user to check access for
        
    Returns:
        Account if found and authorized
        
    Raises:
        NotAuthorized: If user doesn't match the account's user_id
        NotFound: If account doesn't exist
    """
    if not account_id:
        raise NotFound("Account ID is required")
        
    account = get_account(account_id)
    if not account:
        raise NotFound(f"Account {account_id} not found")
        
    if account.user_id != user_id:
        raise NotAuthorized(f"User {user_id} not authorized to access account {account_id}")
        
    return account

def checked_optional_account(account_id: Optional[uuid.UUID], user_id: str) -> Optional[Account]:
    """Check if account exists and user has access to it, allowing None."""
    if not account_id:
        return None
    account = get_account(account_id)
    if not account:
        return None
    if account.user_id != user_id:
        raise NotAuthorized("Not authorized to access this account")
    return account

def checked_mandatory_transaction_file(file_id: uuid.UUID, user_id: str) -> TransactionFile:
    """
    Check if a transaction file exists and the user has access to it.
    
    Args:
        file_id: ID of the file to check
        user_id: ID of the user to check access for
        
    Returns:
        TransactionFile if found and authorized
        
    Raises:
        NotAuthorized: If user doesn't match the file's user_id
        NotFound: If file doesn't exist
    """
    if not file_id:
        raise NotFound("File ID is required")
        
    file = get_transaction_file(file_id)
    if not file:
        raise NotFound(f"File {file_id} not found")
        
    if file.user_id != user_id:
        raise NotAuthorized(f"User {user_id} not authorized to access file {file_id}")
        
    return file

def checked_optional_transaction_file(file_id: Optional[uuid.UUID], user_id: str) -> Optional[TransactionFile]:
    """
    Check if a transaction file exists and the user has access to it, but allow it to not exist.
    
    Args:
        file_id: ID of the file to check
        user_id: ID of the user to check access for
        
    Returns:
        TransactionFile if found and authorized, None if not found
        
    Raises:
        NotAuthorized: If user doesn't match the file's user_id
    """
    if not file_id:
        return None
        
    file = get_transaction_file(file_id)
    if not file:
        return None
        
    if file.user_id != user_id:
        raise NotAuthorized(f"User {user_id} not authorized to access file {file_id}")
        
    return file

def checked_optional_file_map(file_map_id: Optional[uuid.UUID], user_id: str) -> Optional[FileMap]:
    """
    Check if a file map exists and the user has access to it, but allow it to not exist.
    
    Args:
        file_map_id: ID of the file map to check
        user_id: ID of the user to check access for
        
    Returns:
        FileMap if found and authorized, None if not found
        
    Raises:
        NotAuthorized: If user doesn't match the file map's user_id
    """
    if not file_map_id:
        return None
        
    file_map = get_file_map(file_map_id)
    if not file_map:
        return None
        
    if file_map.user_id != user_id:
        raise NotAuthorized(f"User {user_id} not authorized to access file map {file_map_id}")
        
    return file_map 