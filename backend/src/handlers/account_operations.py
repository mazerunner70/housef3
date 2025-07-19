import json
import logging
import os
import traceback
import uuid
import boto3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from decimal import Decimal

from models.account import (
    Account, 
    AccountType, 
    AccountCreate, 
    AccountUpdate,
    convert_currency_input
)
from models.money import Money, Currency
from models.transaction_file import TransactionFile, TransactionFileCreate, FileFormat
from models.transaction import Transaction
from utils.db_utils import (
    get_account,
    list_user_accounts,
    create_account,
    update_account,
    delete_account,
    list_account_files,
    delete_file_metadata,
    delete_transactions_for_file,
    list_account_transactions,
    list_file_transactions,
    checked_mandatory_account
)
from utils.auth import get_user_from_event
from utils.lambda_utils import mandatory_body_parameter, mandatory_path_parameter, mandatory_query_parameter, optional_body_parameter
from utils.s3_dao import generate_upload_url

# Event-driven architecture imports
from services.event_service import event_service
from models.events import AccountCreatedEvent, AccountUpdatedEvent, AccountDeletedEvent

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Fix imports for Lambda environment
try:
    # Try direct imports for Lambda environment
    import sys
    # Add the /var/task (Lambda root) to the path if not already there
    if '/var/task' not in sys.path:
        sys.path.insert(0, '/var/task')
    
    # Add the parent directory to allow direct imports
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # Now try the imports
    from models.account import Account, AccountType, Currency
    from utils.db_utils import get_account, list_user_accounts, create_account, update_account, delete_account
    from utils.db_utils import list_account_files, create_transaction_file
    from models.transaction_file import TransactionFile, FileFormat, ProcessingStatus
    
    logger.info("Successfully imported modules using adjusted path")
except ImportError as e:
    logger.error(f"Import error: {str(e)}")
    # Log the current sys.path to debug import issues
    logger.error(f"Current sys.path: {sys.path}")
    # Last resort, try relative import
    try:
        from ..models.account import Account, AccountType, Currency
        from ..utils.db_utils import get_account, list_user_accounts, create_account, update_account, delete_account
        from ..utils.db_utils import list_account_files, create_transaction_file
        from ..models.transaction_file import TransactionFile, FileFormat, ProcessingStatus
        logger.info("Successfully imported modules using relative imports")
    except ImportError as e2:
        logger.error(f"Final import attempt failed: {str(e2)}")
        raise

# Custom JSON encoder to handle Decimal values
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super(DecimalEncoder, self).default(obj)

def create_response(status_code: int, body: Any) -> Dict[str, Any]:
    """Create an API Gateway response object."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
        },
        "body": json.dumps(body, cls=DecimalEncoder)
    }

def create_account_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Create a new financial account."""
    try:
        account_name = mandatory_body_parameter(event, 'accountName')
        account_type = mandatory_body_parameter(event, 'accountType')
        currency = mandatory_body_parameter(event, 'currency')
        institution = optional_body_parameter(event, 'institution')
        balance = optional_body_parameter(event, 'balance')
        notes = optional_body_parameter(event, 'notes')
        is_active = optional_body_parameter(event, 'isActive')
        default_field_map_id = optional_body_parameter(event, 'defaultfileMapid')

        # Convert currency input to Currency enum
        currency_enum = convert_currency_input(currency)
        
        account = Account(
            userId=user_id,
            accountId=uuid.uuid4(),
            accountName=account_name,
            accountType=AccountType(account_type),
            currency=currency_enum,
            institution=institution,
            balance=Decimal(balance),
            notes=notes,
            isActive=bool(is_active) if is_active is not None else True,
            defaultFileMapId=uuid.UUID(default_field_map_id) if default_field_map_id else None
        )

        # Validate and create the account
        create_account(account)
        
        # Publish account creation event
        try:
            create_event = AccountCreatedEvent(
                user_id=user_id,
                account_id=str(account.account_id),
                account_name=account.account_name,
                account_type=account.account_type.value,
                currency=account.currency.value if account.currency else 'USD'
            )
            event_service.publish_event(create_event)
            logger.info(f"AccountCreatedEvent published for account creation: {account.account_id}")
        except Exception as e:
            logger.warning(f"Failed to publish account creation event: {str(e)}")
        
        # Return the created account
        account_dict = account.model_dump(by_alias=True)
        
        return create_response(201, {
            'message': 'Account created successfully',
            'account': account_dict
        })
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(400, {"message": str(e)})
    except Exception as e:
        logger.error(f"Error creating account: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"message": "Error creating account"})

def get_account_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Get a specific account by ID."""
    try:
        # Get account ID from path parameters
        account_id = mandatory_path_parameter(event, 'id')

        # Get the account
        account = checked_mandatory_account(uuid.UUID(account_id), user_id)
        
        # Convert account to dictionary
        account_dict = account.model_dump(by_alias=True)
        logger.info(f"Account: {account_dict}") 
        return create_response(200, {
            'account': account_dict
        })
    except Exception as e:
        logger.error(f"Error getting account: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"message": "Error retrieving account"})

def list_accounts_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """List all accounts for the current user."""
    try:
        
        # Get accounts for the user
        accounts = list_user_accounts(user_id)
        
        # Convert accounts to dictionary format
        account_dicts = [account.model_dump(by_alias=True) for account in accounts]
        
        return create_response(200, {
            'accounts': account_dicts,
            'user': user_id,
            'metadata': {
                'totalAccounts': len(account_dicts)
            }
        })
    except Exception as e:
        # Always log stacktrace
        logger.error(f"Error listing accounts: {str(e)}") 
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"message": "Error listing accounts"})

def update_account_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Update an existing account."""
    try:
        # Get account ID from path parameters
        account_id = mandatory_path_parameter(event, 'id')
        account_name = optional_body_parameter(event, 'accountName')
        account_type = optional_body_parameter(event, 'accountType')
        currency = optional_body_parameter(event, 'currency')
        institution = optional_body_parameter(event, 'institution')
        balance = optional_body_parameter(event, 'balance')
        notes = optional_body_parameter(event, 'notes')
        is_active = optional_body_parameter(event, 'isActive')
        default_field_map_id = optional_body_parameter(event, 'defaultfileMapid')
        
        # Convert currency input to Currency enum if provided
        currency_enum = convert_currency_input(currency) if currency is not None else None
        
        # Get original account for change tracking
        original_account = get_account(uuid.UUID(account_id))
        
        # Update the account
        updated_account = update_account(uuid.UUID(account_id), user_id, {
            'account_name': account_name,
            'account_type': account_type,
            'currency': currency_enum,
            'institution': institution,
            'balance': balance,
            'notes': notes,
            'is_active': is_active,
            'default_file_map_id': default_field_map_id
        })
        
        # Publish account update event
        try:
            # Track changes
            changes = []
            if original_account and updated_account:
                if original_account.account_name != updated_account.account_name:
                    changes.append({
                        'field': 'accountName',
                        'oldValue': original_account.account_name,
                        'newValue': updated_account.account_name
                    })
                if original_account.account_type != updated_account.account_type:
                    changes.append({
                        'field': 'accountType',
                        'oldValue': original_account.account_type.value,
                        'newValue': updated_account.account_type.value
                    })
                # Add other fields as needed
            
            update_event = AccountUpdatedEvent(
                user_id=user_id,
                account_id=account_id,
                changes=changes
            )
            event_service.publish_event(update_event)
            logger.info(f"AccountUpdatedEvent published for account update: {account_id}")
        except Exception as e:
            logger.warning(f"Failed to publish account update event: {str(e)}")
        
        # Return the updated account
        account_dict = updated_account.model_dump(by_alias=True)
        
        return create_response(200, {
            'message': 'Account updated successfully',
            'account': account_dict
        })
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(400, {"message": str(e)})
    except Exception as e:
        logger.error(f"Error updating account: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"message": "Error updating account"})

def delete_account_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Delete an account."""
    try:
        # Get account ID from path parameters
        account_id = mandatory_path_parameter(event, 'id')
        
        # Verify the account exists and belongs to the user
        account_to_delete = checked_mandatory_account(uuid.UUID(account_id), user_id)
        
        # Delete the account
        delete_account(uuid.UUID(account_id), user_id)
        
        # Publish account deletion event
        try:
            # TODO: Get actual transaction count for this account
            transaction_count = 0  # Would need to count transactions before deletion
            
            delete_event = AccountDeletedEvent(
                user_id=user_id,
                account_id=account_id,
                transaction_count=transaction_count
            )
            event_service.publish_event(delete_event)
            logger.info(f"AccountDeletedEvent published for account deletion: {account_id}")
        except Exception as e:
            logger.warning(f"Failed to publish account deletion event: {str(e)}")
        
        return create_response(200, {
            'message': 'Account deleted successfully',
            'accountId': account_id
        })
    except Exception as e:
        logger.error(f"Error deleting account: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"message": "Error deleting account"})

def account_files_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """List all files associated with an account."""
    try:
        # Get account ID from path parameters
        account_id = mandatory_path_parameter(event, 'id')
        
        # Verify the account exists and belongs to the user
        existing_account = checked_mandatory_account(uuid.UUID(account_id), user_id)
        
        # Get files for the account
        files = list_account_files(uuid.UUID(account_id))
        
        # Convert files to dictionary format
        file_dicts = [file.model_dump(by_alias=True) for file in files]
        
        return create_response(200, {
            'files': file_dicts,
            'user': user_id,
            'metadata': {
                'totalFiles': len(file_dicts),
                'accountId': account_id,
                'accountName': existing_account.account_name
            }
        })
    except Exception as e:
        logger.error(f"Error listing account files: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"message": "Error listing account files"})

def delete_account_files_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Delete all files and their transactions for an account."""
    try:
        # Get account ID from path parameters
        account_id = mandatory_path_parameter(event, 'id')
        
        # Verify the account exists and belongs to the user
        existing_account = checked_mandatory_account(uuid.UUID(account_id), user_id)
        
        # Get all files for the account
        files = list_account_files(uuid.UUID(account_id))
        total_files = len(files)
        total_transactions = 0
        
        # Delete each file and its transactions
        for file in files:
            try:
                # First delete all transactions associated with the file
                transactions_deleted = delete_transactions_for_file(file.file_id)
                total_transactions += transactions_deleted
                
                # Then delete the file metadata itself
                delete_file_metadata(file.file_id)
                logger.info(f"Deleted file {file.file_id} and its {transactions_deleted} transactions")
            except Exception as file_error:
                logger.error(f"Error deleting file {file.file_id}: {str(file_error)}")
                logger.error(f"Stacktrace: {traceback.format_exc()}")
                raise
                # Continue with other files
        
        return create_response(200, {
            'message': 'Account files deleted successfully',
            'metadata': {
                'totalFiles': total_files,
                'totalTransactions': total_transactions,
                'accountId': account_id,
                'accountName': existing_account.account_name
            }
        })
    except Exception as e:
        logger.error(f"Error deleting account files: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"message": "Error deleting account files"})

def account_file_upload_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Create a pre-signed URL for uploading a file to S3 and associate it with an account."""

    account_id = mandatory_path_parameter(event, 'id')
    account = checked_mandatory_account(uuid.UUID(account_id), user_id)
    file_name = mandatory_body_parameter(event, 'fileName')
    content_type = mandatory_body_parameter(event, 'contentType')
    file_size = mandatory_body_parameter(event, 'fileSize')
    file_format_id = optional_body_parameter(event, 'fileFormatId')
    
    
    # Generate a unique file ID
    file_id = str(uuid.uuid4())
    
    # Get bucket name from environment variables
    bucket_name = os.environ.get('FILE_STORAGE_BUCKET')
    if not bucket_name:
        logger.error("FILE_STORAGE_BUCKET environment variable not set")
        return create_response(500, {"message": "Server configuration error"})
        
    # Create S3 key using the generated file ID
    s3_key = f"{user_id}/{file_id}/{file_name}"

    # Generate presigned URL for S3 upload
    upload_url = generate_upload_url(
        user_id,
        file_id,
        file_name,
        content_type,
        bucket_name
    )

    
    # Determine file format based on filename or content type
    file_format = FileFormat.OTHER
    if file_format_id:
        file_format = FileFormat(file_format_id)
    elif file_name.lower().endswith(('.csv')):
        file_format = FileFormat.CSV
    elif file_name.lower().endswith(('.ofx', '.qfx')):
        file_format = FileFormat.OFX
    elif file_name.lower().endswith('.qif'):
        file_format = FileFormat.QIF
    elif file_name.lower().endswith('.pdf'):
        file_format = FileFormat.PDF
    elif file_name.lower().endswith('.xlsx'):
        file_format = FileFormat.XLSX
    
    # Create transaction file record in DynamoDB
    dto_data = {
        'user_id': user_id,
        'file_name': file_name,
        'file_size': int(file_size),
        's3_key': s3_key,
        'file_format': file_format,
        'currency': None, # Optional field in DTO, TransactionFile.currency is also Optional
    }
    if account_id:
        dto_data['account_id'] = account_id
    
    transaction_file_create_dto = TransactionFileCreate(**dto_data)
    
    # Convert DTO to full TransactionFile entity with specified file_id
    transaction_file = transaction_file_create_dto.to_transaction_file(
        file_id=uuid.UUID(file_id)
    )

    create_transaction_file(transaction_file)

    return create_response(201, {
        'message': 'File uploaded successfully',
        'file': transaction_file.model_dump(by_alias=True)
        })


def delete_all_accounts_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Delete all accounts for the current user."""
    try:
        # Get all accounts for the user
        accounts = list_user_accounts(user_id)
        
        # Delete each account
        for account in accounts:
            delete_account(account.account_id, user_id)
        
        return create_response(200, {
            'message': 'All accounts deleted successfully',
            'deletedCount': len(accounts)
        })
    except Exception as e:
        logger.error(f"Error deleting all accounts: {str(e)}")
        return create_response(500, {"message": "Error deleting accounts"})

def get_account_transactions_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Get paginated transactions for an account."""
    try:
        logger.info(f"Starting get_account_transactions_handler with event: {json.dumps(event)}")
        
        # Get account ID from path parameters
        account_id = mandatory_path_parameter(event, 'id')
        logger.info(f"Account ID from path parameters: {account_id}")
        
        # Verify the account exists and belongs to the user
        logger.info(f"Fetching account with ID: {account_id}")
        existing_account = checked_mandatory_account(uuid.UUID(account_id), user_id)

        # Get query parameters for pagination
        query_params = event.get('queryStringParameters', {}) or {}
        
        
        limit = int(mandatory_query_parameter(event, 'limit'))
        last_evaluated_key = event.get('queryStringParameters', {}).get('lastEvaluatedKey')
        
        # Get transactions for the account
        try:
            transactions = list_account_transactions(account_id, limit, last_evaluated_key)
            logger.info(f"Retrieved {len(transactions)} transactions")
        except Exception as tx_error:
            logger.error(f"Error fetching transactions: {str(tx_error)}")
            logger.error(f"Error type: {type(tx_error).__name__}")
            raise
        
        # Convert transactions to dictionary format
        transaction_dicts = [transaction.model_dump(by_alias=True) for transaction in transactions]
        logger.info(f"Converted {len(transaction_dicts)} transactions to dictionary format")
        
        return create_response(200, {
            'transactions': transaction_dicts,
            'metadata': {
                'totalTransactions': len(transaction_dicts),
                'accountId': account_id,
                'accountName': existing_account.account_name
            }
        })
    except Exception as e:
        logger.error(f"Error in get_account_transactions_handler: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Full error details: {json.dumps(e.__dict__) if hasattr(e, '__dict__') else 'No additional error details'}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"message": "Error retrieving account transactions"})

def account_file_timeline_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Return timeline data for all files in an account (fileId, fileName, startDate, endDate, transactionCount, transactionDates)."""
    try:
        account_id = mandatory_path_parameter(event, 'id')

        # Verify the account exists and belongs to the user
        account = checked_mandatory_account(uuid.UUID(account_id), user_id)


        files = list_account_files(uuid.UUID(account_id))
        timeline = []
        for file in files:
            # Always fetch transactions for transactionDates
            transactions = []
            try:
                transactions = list_file_transactions(file.file_id)
            except Exception as e:
                logger.error(f"Error listing transactions for file {file.file_id}: {str(e)}")
            tx_dates = []
            if transactions:
                dates = [t.date for t in transactions if t.date]
                tx_dates = []
                for d in dates:
                    try:
                        # Try ms since epoch
                        iso = datetime.utcfromtimestamp(int(d)/1000).strftime('%Y-%m-%d')
                        tx_dates.append(iso)
                    except Exception:
                        # Fallback: use as string (first 10 chars)
                        tx_dates.append(str(d)[:10])
            # Prefer date_range_start/end if present, else compute from tx_dates
            start = file.date_range.start_date if file.date_range and file.date_range.start_date else None
            end = file.date_range.end_date if file.date_range and file.date_range.end_date else None
            if not (start and end) and tx_dates:
                start = min(tx_dates)
                end = max(tx_dates)
            tx_count = file.record_count if file.record_count is not None else (len(tx_dates) if tx_dates else None)
            timeline.append({
                'fileId': file.file_id,
                'fileName': file.file_name,
                'startDate': start,
                'endDate': end,
                'transactionCount': tx_count,
                'transactionDates': tx_dates
            })
        return create_response(200, {'timeline': timeline, 'accountId': account_id})
    except Exception as e:
        logger.error(f"Error building file timeline: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"message": "Error building file timeline"})

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main handler for account operations."""
    try:
        # Get user from Cognito
        user = get_user_from_event(event)
        if not user:
            return create_response(401, {"message": "Unauthorized"})
        user_id = user['id']
        # Get route from event
        route = event.get('routeKey')
        if not route:
            return create_response(400, {"message": "Route not specified"})
        
            # Log request details
                # Get the HTTP method and route
        method = event.get("requestContext", {}).get("http", {}).get("method", "").upper()
        logger.info(f"Request: {route}")
        
        # Route to appropriate handler
        if route == "GET /accounts":
            return list_accounts_handler(event, user_id)
        elif route == "POST /accounts":
            return create_account_handler(event, user_id)
        elif route == "GET /accounts/{id}":
            return get_account_handler(event, user_id)
        elif route == "PUT /accounts/{id}":
            return update_account_handler(event, user_id)
        elif route == "DELETE /accounts/{id}":
            return delete_account_handler(event, user_id)
        elif route == "DELETE /accounts":
            return delete_all_accounts_handler(event, user_id)
        elif route == "GET /accounts/{id}/files":
            return account_files_handler(event, user_id)
        elif route == "POST /accounts/{id}/files":
            return account_file_upload_handler(event, user_id)
        elif route == "DELETE /accounts/{id}/files":
            return delete_account_files_handler(event, user_id)
        elif route == "GET /accounts/{id}/transactions":
            return get_account_transactions_handler(event, user_id)
        elif route == "GET /accounts/{id}/timeline":
            return account_file_timeline_handler(event, user_id)
        else:
            return create_response(400, {"message": f"Unsupported route: {route}"})
    except Exception as e:
        logger.error(f"Error in account operations handler: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"message": "Internal server error"}) 