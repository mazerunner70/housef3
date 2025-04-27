from typing import List, Dict, Any, Optional
from datetime import datetime
from utils.db_utils import list_account_files, list_user_files, get_field_map


def get_files_for_user(user_id: str, account_id: Optional[str] = None) -> List[dict]:
    """
    Retrieve files for a user, optionally filtered by account.
    """
    if account_id:
        return list_account_files(account_id)
    else:
        return list_user_files(user_id)

def get_files_for_account(account_id: str) -> list:
    """
    Retrieve files for an account.
    """
    return list_account_files(account_id) 

def format_file_metadata(file: dict) -> dict:
    """
    Format a file record from DynamoDB into API response format, including field map details if present.
    """
    formatted = {
        'fileId': file.get('fileId'),
        'fileName': file.get('fileName'),
        'contentType': file.get('contentType'),
        'fileSize': file.get('fileSize'),
        'uploadDate': file.get('uploadDate'),
        'lastModified': file.get('lastModified', file.get('uploadDate'))
    }
    # Add optional fields
    for key in ['accountId', 'fileFormat', 'processingStatus', 'recordCount', 'dateRange', 'errorMessage']:
        if key in file:
            formatted[key] = file.get(key)
    if 'openingBalance' in file:
        formatted['openingBalance'] = float(file.get('openingBalance'))
    if 'fieldMapId' in file:
        formatted['fieldMapId'] = file.get('fieldMapId')
        field_map = get_field_map(file.get('fieldMapId'))
        if field_map:
            formatted['fieldMap'] = {
                'fieldMapId': field_map.field_map_id,
                'name': field_map.name,
                'description': field_map.description
            }
    return formatted 

