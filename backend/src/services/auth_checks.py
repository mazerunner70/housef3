"""
Authorization check functions.
"""
from typing import Optional

from models.account import Account
from models.file_map import FileMap
from models.transaction_file import TransactionFile
from utils.db_utils import get_account, get_file_map, get_transaction_file
from utils.auth import NotAuthorized, NotFound

def checked_mandatory_account(account_id: Optional[str], user_id: str) -> Account:
    """Check if account exists and user has access to it."""
    account = checked_optional_account(account_id, user_id)
    if not account:
        raise NotFound("Account not found")
    return account

def checked_optional_account(account_id: Optional[str], user_id: str) -> Optional[Account]:
    """Check if account exists and user has access to it, allowing None."""
    if not account_id:
        return None
    account = get_account(account_id)
    if not account:
        return None
    if account.user_id != user_id:
        raise NotAuthorized("Not authorized to access this account")
    return account

def checked_mandatory_transaction_file(file_id: str, user_id: str) -> TransactionFile:
    """Check if file exists and user has access to it."""
    file = checked_optional_transaction_file(file_id, user_id)
    if not file:
        raise NotFound("File not found")
    return file

def checked_optional_transaction_file(file_id: Optional[str], user_id: str) -> Optional[TransactionFile]:
    """Check if file exists and user has access to it, allowing None."""
    if not file_id:
        return None
    file = get_transaction_file(file_id)
    if not file:
        return None
    if file.user_id != user_id:
        raise NotAuthorized("Not authorized to access this file")
    return file

def checked_mandatory_file_map(file_map_id: Optional[str], user_id: str) -> FileMap:
    """Check if file map exists and user has access to it."""
    file_map = checked_optional_file_map(file_map_id, user_id)
    if not file_map:
        raise NotFound("File mapping not found")
    return file_map

def checked_optional_file_map(file_map_id: Optional[str], user_id: str) -> Optional[FileMap]:
    """Check if file map exists and user has access to it, allowing None."""
    if not file_map_id:
        return None
    file_map = get_file_map(file_map_id)
    if not file_map:
        return None
    if file_map.user_id != user_id:
        raise NotAuthorized("Not authorized to access this field mapping")
    return file_map 