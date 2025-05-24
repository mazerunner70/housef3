from typing import List, Dict, Any, Optional
from datetime import datetime
from models.transaction_file import TransactionFile
from utils.db_utils import get_file_map, list_account_files, list_user_files

FIELD_MAP = {
    'accountId': 'account_id',
    'fileFormat': 'file_format',
    'processingStatus': 'processing_status',
    'recordCount': 'record_count',
    'dateRange': 'date_range'
}

def get_files_for_user(user_id: str, account_id: Optional[str] = None) -> List[TransactionFile]:
    """
    Retrieve files for a user, optionally filtered by account.
    """
    if account_id:
        return list_account_files(account_id)
    else:
        return list_user_files(user_id)

def get_files_for_account(account_id: str) -> List[TransactionFile]:
    """
    Retrieve files for an account.
    """
    return list_account_files(account_id) 

def format_file_metadata(file: TransactionFile) -> Dict[str, Any]:
    """
    Format a file record from DynamoDB into API response format, including field map details if present.
    """
    formatted = file.to_dict()
    # Add optional fields    
    for camel, snake in FIELD_MAP.items():
        value = getattr(file, snake, None)
        if value is not None:
            formatted[camel] = value

    # Override openingBalance with just the numeric amount for frontend compatibility
    if file.opening_balance:
        formatted['openingBalance'] = float(file.opening_balance.amount)
    
    if file.file_map_id:
        field_map = get_file_map(file.file_map_id)
        if field_map:
            formatted['fieldMap'] = {
                'fieldMapId': field_map.file_map_id,
                'name': field_map.name,
                'description': field_map.description
            }
    return formatted 

