import json
import logging
import os
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any
from decimal import Decimal

from models.account import (
    Account,
    AccountCreate,
    AccountUpdate,
    AccountType,
)
from utils.serde_utils import to_currency
from models.transaction_file import FileFormat, TransactionFileCreate
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
    checked_mandatory_account,
    create_transaction_file,
)
from utils.auth import get_user_from_event
from utils.lambda_utils import (
    create_response,
    mandatory_body_parameter,
    mandatory_path_parameter,
    mandatory_query_parameter,
    optional_body_parameter,
    parse_and_validate_json,
)
from utils.s3_dao import generate_upload_url
from utils.handler_decorators import api_handler, standard_error_handling, require_authenticated_user

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
    if "/var/task" not in sys.path:
        sys.path.insert(0, "/var/task")

    # Add the parent directory to allow direct imports
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    # Now try the imports
    from models.account import Account, AccountType, Currency
    from utils.db_utils import (
        get_account,
        list_user_accounts,
        create_account,
        update_account,
        delete_account,
    )
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
        from ..utils.db_utils import (
            get_account,
            list_user_accounts,
            create_account,
            update_account,
            delete_account,
        )
        from ..utils.db_utils import list_account_files, create_transaction_file
        from ..models.transaction_file import (
            TransactionFile,
            FileFormat,
            ProcessingStatus,
        )

        logger.info("Successfully imported modules using relative imports")
    except ImportError as e2:
        logger.error(f"Final import attempt failed: {str(e2)}")
        raise


# Note: Using centralized create_response and DecimalEncoder from utils.lambda_utils
# This ensures consistent JSON serialization across all handlers


@api_handler()
def create_account_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Create a new financial account using Pydantic DTO pattern."""
    # Parse and validate JSON using Pydantic DTO
    account_data, error_response = parse_and_validate_json(event, AccountCreate)
    if error_response:
        # Return validation error (status handled by decorator)
        raise ValueError(error_response["message"])
    
    # account_data is guaranteed to be valid AccountCreate here
    assert account_data is not None
    
    # Convert AccountCreate to Account
    account_create_data = account_data.model_dump()
    account_create_data["user_id"] = user_id  # Override with authenticated user_id
    
    account = Account(
        accountId=uuid.uuid4(),  # Generate new ID
        **account_create_data
    )

    # Create and publish event
    create_account(account)
    
    try:
        create_event = AccountCreatedEvent(
            user_id=user_id,
            account_id=str(account.account_id),
            account_name=account.account_name,
            account_type=account.account_type.value,
            currency=account.currency.value if account.currency else None,
        )
        event_service.publish_event(create_event)
        logger.info(f"AccountCreatedEvent published for account creation: {account.account_id}")
    except Exception as e:
        logger.warning(f"Failed to publish account creation event: {str(e)}")

    return {
        "message": "Account created successfully", 
        "account": account.model_dump(by_alias=True, mode='json')
    }


@api_handler(require_ownership=("id", "account"))
def get_account_handler(event: Dict[str, Any], user_id: str, account: Account) -> Dict[str, Any]:
    """Get a specific account by ID."""
    # Account ownership already verified by decorator
    return {"account": account.model_dump(by_alias=True, mode='json')}


@api_handler()
def list_accounts_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """List all accounts for the current user."""
    accounts = list_user_accounts(user_id)
    account_dicts = [account.model_dump(by_alias=True, mode='json') for account in accounts]
    
    return {
        "accounts": account_dicts,
        "user": user_id,
        "metadata": {"totalAccounts": len(account_dicts)},
    }


@api_handler(require_ownership=("id", "account"))
def update_account_handler(event: Dict[str, Any], user_id: str, account: Account) -> Dict[str, Any]:
    """Update an existing account using Pydantic DTO pattern."""
    # Parse and validate JSON using Pydantic DTO
    update_data, error_response = parse_and_validate_json(event, AccountUpdate)
    if error_response:
        # Return validation error (status handled by decorator)
        raise ValueError(error_response["message"])
    
    # update_data is guaranteed to be valid AccountUpdate here
    assert update_data is not None
    
    # Convert AccountUpdate to update dict (only non-None fields)
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}

    # Update account
    updated_account = update_account(account.account_id, user_id, update_dict)

    # Publish update event
    try:
        changes = []
        if account.account_name != updated_account.account_name:
            changes.append({
                "field": "accountName",
                "oldValue": account.account_name,
                "newValue": updated_account.account_name,
            })
        
        update_event = AccountUpdatedEvent(
            user_id=user_id, 
            account_id=str(account.account_id), 
            changes=changes
        )
        event_service.publish_event(update_event)
        logger.info(f"AccountUpdatedEvent published for account update: {account.account_id}")
    except Exception as e:
        logger.warning(f"Failed to publish account update event: {str(e)}")

    return {
        "message": "Account updated successfully", 
        "account": updated_account.model_dump(by_alias=True, mode='json')
    }


@api_handler(require_ownership=("id", "account"))
def delete_account_handler(event: Dict[str, Any], user_id: str, account: Account) -> Dict[str, Any]:
    """Delete an account."""
    # Delete the account
    delete_account(account.account_id, user_id)

    # Publish deletion event
    try:
        delete_event = AccountDeletedEvent(
            user_id=user_id,
            account_id=str(account.account_id),
            transaction_count=0,  # TODO: Get actual count
        )
        event_service.publish_event(delete_event)
        logger.info(f"AccountDeletedEvent published for account deletion: {account.account_id}")
    except Exception as e:
        logger.warning(f"Failed to publish account deletion event: {str(e)}")

    return {
        "message": "Account deleted successfully", 
        "accountId": str(account.account_id)
    }


@api_handler(require_ownership=("id", "account"))
def account_files_handler(event: Dict[str, Any], user_id: str, account: Account) -> Dict[str, Any]:
    """List all files associated with an account."""
    files = list_account_files(account.account_id)
    file_dicts = [file.model_dump(by_alias=True, mode='json') for file in files]

    return {
        "files": file_dicts,
        "user": user_id,
        "metadata": {
            "totalFiles": len(file_dicts),
            "accountId": str(account.account_id),
            "accountName": account.account_name,
        },
    }


def delete_account_files_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Delete all files and their transactions for an account."""
    try:
        # Get account ID from path parameters
        account_id = mandatory_path_parameter(event, "id")

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
                logger.info(
                    f"Deleted file {file.file_id} and its {transactions_deleted} transactions"
                )
            except Exception as file_error:
                logger.error(f"Error deleting file {file.file_id}: {str(file_error)}")
                logger.error(f"Stacktrace: {traceback.format_exc()}")
                raise
                # Continue with other files

        return create_response(
            200,
            {
                "message": "Account files deleted successfully",
                "metadata": {
                    "totalFiles": total_files,
                    "totalTransactions": total_transactions,
                    "accountId": account_id,
                    "accountName": existing_account.account_name,
                },
            },
        )
    except Exception as e:
        logger.error(f"Error deleting account files: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"message": "Error deleting account files"})


def account_file_upload_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Create a pre-signed URL for uploading a file to S3 and associate it with an account."""

    account_id = mandatory_path_parameter(event, "id")
    account = checked_mandatory_account(uuid.UUID(account_id), user_id)
    file_name = mandatory_body_parameter(event, "fileName")
    content_type = mandatory_body_parameter(event, "contentType")
    file_size = mandatory_body_parameter(event, "fileSize")
    file_format_id = optional_body_parameter(event, "fileFormatId")

    # Generate a unique file ID
    file_id = str(uuid.uuid4())

    # Get bucket name from environment variables
    bucket_name = os.environ.get("FILE_STORAGE_BUCKET")
    if not bucket_name:
        logger.error("FILE_STORAGE_BUCKET environment variable not set")
        return create_response(500, {"message": "Server configuration error"})

    # Create S3 key using the generated file ID
    s3_key = f"{user_id}/{file_id}/{file_name}"

    # Generate presigned URL for S3 upload
    upload_url = generate_upload_url(
        user_id, file_id, file_name, content_type, bucket_name
    )

    # Determine file format based on filename or content type
    file_format = FileFormat.OTHER
    if file_format_id:
        file_format = FileFormat(file_format_id)
    elif file_name.lower().endswith((".csv")):
        file_format = FileFormat.CSV
    elif file_name.lower().endswith((".ofx", ".qfx")):
        file_format = FileFormat.OFX
    elif file_name.lower().endswith(".qif"):
        file_format = FileFormat.QIF
    elif file_name.lower().endswith(".pdf"):
        file_format = FileFormat.PDF
    elif file_name.lower().endswith(".xlsx"):
        file_format = FileFormat.XLSX

    # Create transaction file record in DynamoDB
    dto_data = {
        "user_id": user_id,
        "file_name": file_name,
        "file_size": int(file_size),
        "s3_key": s3_key,
        "file_format": file_format,
        "currency": None,  # Optional field in DTO, TransactionFile.currency is also Optional
    }
    if account_id:
        dto_data["account_id"] = account_id

    transaction_file_create_dto = TransactionFileCreate(**dto_data)

    # Convert DTO to full TransactionFile entity with specified file_id
    transaction_file = transaction_file_create_dto.to_transaction_file(
        file_id=uuid.UUID(file_id)
    )

    create_transaction_file(transaction_file)

    return create_response(
        201,
        {
            "message": "File uploaded successfully",
            "file": transaction_file.model_dump(by_alias=True, mode='json'),
        },
    )


def delete_all_accounts_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Delete all accounts for the current user."""
    try:
        # Get all accounts for the user
        accounts = list_user_accounts(user_id)

        # Delete each account
        for account in accounts:
            delete_account(account.account_id, user_id)

        return create_response(
            200,
            {
                "message": "All accounts deleted successfully",
                "deletedCount": len(accounts),
            },
        )
    except Exception as e:
        logger.error(f"Error deleting all accounts: {str(e)}")
        return create_response(500, {"message": "Error deleting accounts"})


@api_handler(require_ownership=("id", "account"))
def get_account_transactions_handler(event: Dict[str, Any], user_id: str, account: Account) -> Dict[str, Any]:
    """Get paginated transactions for an account."""
    # Get pagination parameters
    limit = int(mandatory_query_parameter(event, "limit"))
    last_evaluated_key = event.get("queryStringParameters", {}).get("lastEvaluatedKey")

    # Get transactions
    transactions = list_account_transactions(str(account.account_id), limit, last_evaluated_key)

    # Convert to response format
    transaction_dicts = [
        transaction.model_dump(by_alias=True, mode="json")
        for transaction in transactions
    ]

    return {
        "transactions": transaction_dicts,
        "metadata": {
            "totalTransactions": len(transaction_dicts),
            "accountId": str(account.account_id),
            "accountName": account.account_name,
        },
    }


def account_file_timeline_handler(
    event: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    """Return timeline data for all files in an account (fileId, fileName, startDate, endDate, transactionCount, transactionDates)."""
    try:
        account_id = mandatory_path_parameter(event, "id")

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
                logger.error(
                    f"Error listing transactions for file {file.file_id}: {str(e)}"
                )
            tx_dates = []
            if transactions:
                dates = [t.date for t in transactions if t.date]
                tx_dates = []
                for d in dates:
                    try:
                        # Try ms since epoch
                        iso = datetime.utcfromtimestamp(int(d) / 1000).strftime(
                            "%Y-%m-%d"
                        )
                        tx_dates.append(iso)
                    except Exception:
                        # Fallback: use as string (first 10 chars)
                        tx_dates.append(str(d)[:10])
            # Prefer date_range_start/end if present, else compute from tx_dates
            start = (
                file.date_range.start_date
                if file.date_range and file.date_range.start_date
                else None
            )
            end = (
                file.date_range.end_date
                if file.date_range and file.date_range.end_date
                else None
            )
            if not (start and end) and tx_dates:
                start = min(tx_dates)
                end = max(tx_dates)
            tx_count = (
                file.record_count
                if file.record_count is not None
                else (len(tx_dates) if tx_dates else None)
            )
            timeline.append(
                {
                    "fileId": file.file_id,
                    "fileName": file.file_name,
                    "startDate": start,
                    "endDate": end,
                    "transactionCount": tx_count,
                    "transactionDates": tx_dates,
                }
            )
        return create_response(200, {"timeline": timeline, "accountId": account_id})
    except Exception as e:
        logger.error(f"Error building file timeline: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"message": "Error building file timeline"})


@require_authenticated_user
@standard_error_handling
def handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Main handler for account operations - much cleaner routing!"""
    route = event.get("routeKey")
    if not route:
        raise ValueError("Route not specified")

    # Route to appropriate handler - no need for individual try/catch blocks
    route_map = {
        "GET /accounts": list_accounts_handler,
        "POST /accounts": create_account_handler,
        "GET /accounts/{id}": get_account_handler,
        "PUT /accounts/{id}": update_account_handler,
        "DELETE /accounts/{id}": delete_account_handler,
        "DELETE /accounts": delete_all_accounts_handler,
        "GET /accounts/{id}/files": account_files_handler,
        "POST /accounts/{id}/files": account_file_upload_handler,
        "DELETE /accounts/{id}/files": delete_account_files_handler,
        "GET /accounts/{id}/transactions": get_account_transactions_handler,
        "GET /accounts/{id}/timeline": account_file_timeline_handler,
    }
    
    handler_func = route_map.get(route)
    if not handler_func:
        raise ValueError(f"Unsupported route: {route}")
    
    return handler_func(event, user_id)
