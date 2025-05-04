import json
import logging
import os
import uuid
from utils.auth import NotFound, checked_mandatory_account, checked_mandatory_file, checked_optional_account
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal
from models.transaction_file import FileFormat, ProcessingStatus, DateRange, validate_transaction_file_data, transaction_file_to_json
from models.transaction import Transaction
from utils.db_utils import get_transaction_file, list_user_files, list_account_files, create_transaction_file, update_file_field_map, update_transaction_file, delete_file_metadata, get_account, list_file_transactions, delete_transactions_for_file, get_field_maps_table, get_field_map
from utils.transaction_parser import file_type_selector, parse_transactions
from utils.s3_dao import (
    get_presigned_url,
    delete_object,
    get_object_content,
    put_object
)
from handlers.file_processor import process_file_with_account
from services.file_service import get_files_for_user, format_file_metadata, get_files_for_account
from utils.lambda_utils import create_response, mandatory_body_parameter, mandatory_path_parameter, handle_error, optional_body_parameter, optional_query_parameter 

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
    from models.transaction_file import TransactionFile, FileFormat, ProcessingStatus, DateRange, validate_transaction_file_data
    from utils.db_utils import get_transaction_file, list_user_files, list_account_files, create_transaction_file, update_transaction_file, delete_file_metadata
    from utils.db_utils import get_account
    
    logger.info("Successfully imported modules using adjusted path")
except ImportError as e:
    logger.error(f"Import error: {str(e)}")
    # Log the current sys.path to debug import issues
    logger.error(f"Current sys.path: {sys.path}")
    # Last resort, try relative import
    try:
        from ..models.transaction_file import TransactionFile, FileFormat, ProcessingStatus, DateRange, validate_transaction_file_data
        from ..utils.db_utils import get_transaction_file, list_user_files, list_account_files, create_transaction_file, update_transaction_file, delete_file_metadata
        from ..utils.db_utils import get_account
        logger.info("Successfully imported modules using relative imports")
    except ImportError as e2:
        logger.error(f"Final import attempt failed: {str(e2)}")
        raise


# Get environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
FILE_STORAGE_BUCKET = os.environ.get('FILE_STORAGE_BUCKET', 'housef3-dev-file-storage')
FILES_TABLE = os.environ.get('FILES_TABLE', 'transaction-files')

if not FILE_STORAGE_BUCKET:
    logger.error("FILE_STORAGE_BUCKET environment variable not set")
    raise ValueError("FILE_STORAGE_BUCKET environment variable not set")


def get_user_from_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract user information from the event."""
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

def generate_file_id() -> str:
    """Generate a unique file ID."""
    return str(uuid.uuid4())



def list_files_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """List files for the current user."""
    try:
        logger.info(f"Listing files for user: {user['id']}")
        account = checked_optional_account(optional_query_parameter(event, 'accountId'), user['id'])
        files = get_files_for_user(user['id'], account.account_id if account else None)
        formatted_files = [format_file_metadata(file) for file in files]
        return create_response(200, {
            'files': formatted_files,
            'user': user,
            'metadata': {
                'totalFiles': len(formatted_files),
                'timestamp': datetime.utcnow().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}, Exception type: {type(e).__name__}")
        return create_response(500, {"message": "Error listing files"})

def get_files_by_account_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """List files for a specific account, with authorization and formatting."""
    try:
        account_id = mandatory_path_parameter(event, 'accountId')
        checked_mandatory_account(account_id, user['id'])
        files = get_files_for_account(account_id)
        formatted_files = [format_file_metadata(file) for file in files]
        return create_response(200, {
            'files': formatted_files,
            'user': user,
            'metadata': {
                'totalFiles': len(formatted_files),
                'timestamp': datetime.utcnow().isoformat(),
                'accountId': account_id
            }
        })
    except PermissionError:
        return create_response(403, {"message": "Access denied. You do not own this account"})
    except ValueError as e:
        return create_response(400, {"message": str(e)})
    except Exception as e:
        logger.error(f"Error listing files for account: {str(e)}, Exception type: {type(e).__name__}")
        return create_response(500, {"message": "Error listing files for account"})

def get_upload_url_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a presigned URL for file upload."""
    try:
        # Parse request body
        file_name = mandatory_body_parameter(event, 'fileName')
        file_size = mandatory_body_parameter(event, 'fileSize')

        account = checked_optional_account(optional_body_parameter(event, 'accountId'), user['id'])
           
        # Validate account_id if it's provided (for account-file association)
        if account:
            logger.info(f"Associating file with account: {account.account_id}")
        else:
            # If not associated with an account, it's a standalone file
            logger.info("Creating a standalone file (no account association)")
            
        # Generate a unique file ID
        file_id = generate_file_id()
        
        # Use user ID as part of the key for organization
        file_key = f"{user['id']}/{file_id}/{file_name}"
        
        # Generate presigned URL for upload
        upload_url = get_presigned_url(FILE_STORAGE_BUCKET, file_key, 'put')
     
        # Store file metadata in DynamoDB
        current_time = datetime.utcnow().isoformat()
        
        # Create basic item with required fields
        item = {
            'fileId': file_id,
            'userId': user['id'],
            'fileName': file_name,
            'fileSize': file_size,
            'uploadDate': current_time,
            'lastModified': current_time,
            's3Key': file_key,
            'processingStatus': ProcessingStatus.PENDING.value,
        }
        
        # Add accountId if provided (for transaction files)
        if account:
            item['accountId'] = account.account_id
        
        logger.info(f"Saving file metadata to DynamoDB: {json.dumps(item)}")
        logger.info(f"User ID for index: {user['id']}")
        
        create_transaction_file(item)
        
        # Create response with basic fields
        response = {
            'fileId': file_id,
            'uploadUrl': upload_url,
            'fileName': file_name,
            'expires': 3600,  # URL expires in 1 hour
            'processingStatus': ProcessingStatus.PENDING.value,
        }
        
        # Include accountId in response if it was provided
        if account:
            response['accountId'] = account.account_id
            
        return create_response(200, response)
    except ValueError as ve:
        return handle_error(400, str(ve))
    except Exception as e:
        logger.error(f"Error generating upload URL: {str(e)}, Exception type: {type(e).__name__}")
        return handle_error(500, "Error generating upload URL")


def get_download_url_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a presigned URL for file download."""
    try:
        # Get file ID from path parameters
        file_id = mandatory_path_parameter(event, 'id')
            
        # Get file metadata from DynamoDB
        file = checked_mandatory_file(file_id, user['id'])
    
        # Generate presigned URL for download
        download_url = get_presigned_url(FILE_STORAGE_BUCKET, file.s3_key, 'get')
        
        return create_response(200, {
            'fileId': file.file_id,
            'downloadUrl': download_url,
            'fileName': file.file_name,
            'contentType': file.content_type,
            'expires': 3600  # URL expires in 1 hour
        })
    except ValueError as ve:        
        return handle_error(400, str(ve))
    except NotFound as e:
        return handle_error(404, str(e))
    except Exception as e:
        logger.error(f"Error generating download URL: {str(e)}")
        return handle_error(500, "Error generating download URL")

def delete_file_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Delete a file and all its associated data.
    
    This handler performs the following operations in sequence:
    1. Validates the request and file ownership
    2. Deletes all associated transactions from DynamoDB
    3. Deletes the file content from S3
    4. Deletes the file metadata from DynamoDB
    5. Verifies the deletion was successful
    
    Args:
        event: API Gateway event containing the file ID in pathParameters
        user: Dictionary containing authenticated user information
        
    Returns:
        API Gateway response with status code and message
    """
    try:
        # Step 1: Request validation and authorization
        # Extract file ID from the request path parameters
        logger.info(f"Deleting file {event}")
        file_id = mandatory_path_parameter(event, 'id')
            
        # Retrieve file metadata to verify existence and ownership
        file = checked_mandatory_file(file_id, user['id'])
            
        # Ensure the file belongs to the requesting user
        if file.user_id != user['id']:
            return create_response(403, {"message": "Access denied"})
        
        # Step 2: Handle account association cleanup
        # Check and log if file is associated with an account for audit purposes
        account_id = None
        if file.account_id:
            account_id = file.account_id
            logger.info(f"File {file_id} is associated with account {account_id}. This association will be removed during deletion.")
            
        # Step 3: Delete associated transactions
        # Remove all transactions linked to this file from DynamoDB
        try:
            transactions_deleted = delete_transactions_for_file(file_id)
            logger.info(f"Deleted {transactions_deleted} transactions for file {file_id}")
        except Exception as tx_error:
            logger.error(f"Error deleting transactions: {str(tx_error)}")
            return create_response(500, {"message": f"Error deleting associated transactions with file {file_id}"})
            
        # Step 4: Delete file content from S3
        # Remove the actual file content from the S3 bucket
        if not delete_object(file.s3_key):
            return create_response(500, {"message": f"Error deleting file from S3 with key {file.s3_key}"})
        
        logger.info(f"Successfully deleted file {file_id} from S3 bucket")
        
        # Step 5: Delete file metadata and verify deletion
        try:
            # Remove the file metadata from DynamoDB
            delete_file_metadata(file_id)
            logger.info(f"Successfully deleted file {file_id} from DynamoDB table")
            
            # Step 6: Verification checks
            # Verify the file metadata was actually deleted
            verification = get_transaction_file(file_id)
            if verification is not None:
                logger.error(f"File {file_id} was not deleted from DynamoDB, instead it is {verification}")
                return create_response(500, {"message": "Error verifying file deletion"})
                
            # If file was associated with an account, verify it's removed from the account index
            if account_id:
                # Check the AccountIdIndex to ensure the file is no longer associated
                account_files = list_account_files(account_id)
                for account_file in account_files:
                    if getattr(account_file, 'file_id', None) == file_id:
                        logger.error(f"File {file_id} still appears in account {account_id} index")
                        # This should never happen if the main item is deleted
            
            logger.info(f"File {file_id} deletion verified")
            
        except Exception as dynamo_error:
            logger.error(f"Error deleting file from DynamoDB: {str(dynamo_error)}")
            return create_response(500, {"message": "Error deleting file metadata from database"})
        
        # Step 7: Return success response with metadata
        return create_response(200, {
            'message': 'File deleted successfully',
            'fileId': file_id,
            'metadata': {
                'transactionsDeleted': transactions_deleted
            }
        })
    except ValueError as e:
        logger.error(f"Error deleting file: {str(e)}", exc_info=True)
        return handle_error(400, str(e))
    except NotFound as e:
        logger.error(f"File not found: {str(e)}", exc_info=True)
        return handle_error(404, str(e))
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}", exc_info=True)
        return create_response(500, {"message": "Error deleting file"})

def unassociate_file_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Remove account association from a file."""
    try:
        # Get file ID from path parameters
        logger.info(f"Unassociating file {event}")
        file_id = mandatory_path_parameter(event, 'id')
           
        # Get file metadata from DynamoDB
        file = checked_mandatory_file(file_id, user['id'])
        
        # Check if file is associated with an account
        if not file.account_id:
            raise ValueError("File is not associated with any account")
        
        account_id = file.accountId
        
        # Update the file to remove account association
        logger.info(f"Removing association between file {file_id} and account {account_id}")
        update_transaction_file(file_id, {'accountId': None})          
        return create_response(200, {
            "message": "File successfully unassociated from account",
            "fileId": file_id,
            "previousAccountId": account_id
        })

    except ValueError as e:
        logger.error(f"Error unassociating file: {str(e)}")
        return handle_error(400, str(e))
    except NotFound as e:
        return handle_error(404, str(e))
    except Exception as e:
        logger.error(f"Error unassociating file: {str(e)}")
        return create_response(500, {"message": "Error handling unassociate request"})

def associate_file_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Associate a file with an account."""
    try:
        # Get file ID from path parameters
        file_id = mandatory_path_parameter(event, 'id')
        
        # Get account ID from request body
        account_id = mandatory_body_parameter(event, 'accountId')
                
        # Get the file to verify it exists and belongs to the user
        file = checked_mandatory_file(file_id, user['id'])
                
        # Check if the file already belongs to the user
        if file.user_id != user['id']:
            raise ValueError("Access denied to the specified file")
                
            # Check if the file is already associated with an account
        if file.account_id:
            logger.info(f"File {file_id} is already associated with account {file.account_id}")
            raise ValueError("File is already associated with an account")   
        
        # Verify that the account exists and belongs to the user
        account = checked_mandatory_account(account_id, user['id'])
            
        # Update the file to add account association
        logger.info(f"Associating file {file_id} with account {account_id}")
        update_transaction_file(file_id, {'account_id': account_id})
        
        # Update the file to add account association
        try:
            logger.info(f"Associating file {file_id} with account {account_id}")      
            update_transaction_file(file_id, {'account_id': account_id})
            # read the account metadata from the account table and check if there is a default mapping apply it to this file

            if account.default_mapping:
                update_file_field_map(file_id, account.default_mapping)
            #next update the openingbalance if there is overlap between this file and the others associated with this account
            process_file_with_account(file_id, file.content, file.file_format, file.opening_balance, user['id'])      
        except Exception as update_error:
            logger.error(f"Error updating file: {str(update_error)}")
            return create_response(500, {"message": "Error associating file with account"})
    except Exception as e:
        logger.error(f"Error associating file: {str(e)}")
        return create_response(500, {"message": "Error handling associate request"})

def update_file_balance_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Update a file's opening balance."""
    try:
        # Get file ID from path parameters
        file_id = mandatory_path_parameter(event, 'id')
            
        # Get file metadata from DynamoDB
        file = checked_mandatory_file(file_id, user['id'])
        
        # Parse the request body to get the opening balance
        opening_balance = Decimal(mandatory_body_parameter(event, 'openingBalance'))
 
        # Update the file with the new opening balance
        try:
            logger.info(f"Updating opening balance for file {file_id} to {opening_balance}")
            
            # Update the file
            update_transaction_file(file_id, {"openingBalance": str(opening_balance)})
            
            # After successfully updating the opening balance, trigger transaction reprocessing
            try:
                logger.info(f"Triggering transaction reprocessing for file {file_id}")
                # Get the file content from S3
                s3_key = file.s3_key
                if not s3_key:
                    logger.error(f"File {file_id} has no S3 key, skipping transaction processing")
                    return create_response(500, {
                        "message": "File has no S3 key, skipping transaction processing",
                        "fileId": file_id,
                    })
                
                # Get file content from S3
                content_bytes = get_object_content(s3_key)
                
                # Get file format
                file_format = FileFormat(file.file_format)
                
                # Process transactions with new opening balance
                transaction_count = process_file_with_account(
                    file_id, 
                    content_bytes, 
                    file_format, 
                    opening_balance,
                    user['id']
                )
                
                # Include transaction count in response
                return create_response(200, {
                    "message": "File opening balance updated successfully and transactions reprocessed",
                    "fileId": file_id,
                    "openingBalance": opening_balance,
                    "transactionCount": transaction_count
                })
            except Exception as process_error:
                logger.error(f"Error processing transactions after balance update: {str(process_error)}")
                # Still return success for the balance update, even if processing failed
                return create_response(200, {
                    "message": "File opening balance updated successfully, but error processing transactions",
                    "fileId": file_id,
                    "openingBalance": opening_balance
                })
        except Exception as update_error:
            logger.error(f"Error updating file: {str(update_error)}")
            return create_response(500, {"message": "Error updating file opening balance"})
    except Exception as e:
        logger.error(f"Error updating file balance: {str(e)}")
        return create_response(500, {"message": "Error handling update balance request"})

def get_file_metadata_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Get metadata for a single file by ID."""
    try:
        # Get file ID from path parameters
        file_id = mandatory_path_parameter(event, 'id') 
        
        # Get file metadata from DynamoDB
        file = checked_mandatory_file(file_id, user['id'])
        
        # Convert to JSON-friendly format with proper type handling
        file_json = json.loads(transaction_file_to_json(file))
        
        # Add field map information if it exists
        if 'fieldMapId' in file_json:
            field_map = get_field_map(file_json['fieldMapId'])
            if field_map:
                file_json['fieldMap'] = {
                    'fieldMapId': field_map.field_map_id,
                    'name': field_map.name,
                    'description': field_map.description
                }
        
        return create_response(200, file_json)
    except Exception as e:
        logger.error(f"Error getting file metadata: {str(e)}")
        return create_response(500, {"message": "Error getting file metadata"})

def get_file_transactions_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Get all transactions for a specific file."""
    try:
        # Get file ID from path parameters
        file_id = mandatory_path_parameter(event, 'id') 

            
        # Get file metadata to verify ownership
        file = checked_mandatory_file(file_id, user['id'])
        
        # Get transactions for the file
        try:
            transactions = list_file_transactions(file_id)

            
            # Sort transactions by date
            transactions.sort(key=lambda x: x.date)
            
            return create_response(200, {
                'fileId': file_id,
                'transactions': [transaction.to_dict() for transaction in transactions],
                'metadata': {
                    'totalTransactions': len(transactions),
                    'timestamp': datetime.utcnow().isoformat()
                }
            })
        except Exception as e:
            logger.error(f"Error retrieving transactions for file {file_id}: {str(e)}")
            return create_response(500, {"message": "Error retrieving transactions"})
            
    except Exception as e:
        logger.error(f"Error in get_file_transactions_handler: {str(e)}")
        return create_response(500, {"message": "Internal server error"})

def delete_file_transactions_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Delete all transactions for a specific file."""
    try:
        # Get file ID from path parameters
        file_id = mandatory_path_parameter(event, 'id')
            
        # Get file metadata to verify ownership
        file = checked_mandatory_file(file_id, user['id'])
        
        # Delete all transactions for the file

        deleted_count = delete_transactions_for_file(file_id)
        
        return create_response(200, {
            'fileId': file_id,
            'message': f'Successfully deleted {deleted_count} transactions',
            'metadata': {
                'deletedCount': deleted_count,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error in delete_file_transactions_handler: {str(e)}")
        return create_response(500, {"message": "Internal server error"})

def get_file_content_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Get the content of a file by ID."""
    try:
        # Get file ID from path parameters
        file_id = mandatory_path_parameter(event, 'id')
  
        # Get file metadata from DynamoDB
        file = checked_mandatory_file(file_id, user['id'])
        
        # Get the file content from S3 using S3 DAO
        content = get_object_content(file.s3_key)
        if content is None:
            return create_response(500, {"message": "Error reading file content"})
            
        return create_response(200, {
            'fileId': file_id,
            'content': content.decode('utf-8'),
            'contentType': file.content_type,
            'fileName': file.file_name
        })
            
    except Exception as e:
        logger.error(f"Error getting file content: {str(e)}")
        return create_response(500, {"message": "Error getting file content"})

def update_file_field_map_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Update a file's field map."""
    try:
        # Get file ID from path parameters
        file_id = mandatory_path_parameter(event, 'id')
        field_map_id = mandatory_body_parameter(event, 'fieldMapId')
            
        # Get file metadata from DynamoDB
        file = checked_mandatory_file(file_id, user['id'])
        
        # Get field map
        field_map = get_field_map(field_map_id)
        if not field_map:
            return create_response(404, {"message": "Field map not found"})
        
        # Update the file to add field map association
        try:
            logger.info(f"Associating file {file_id} with field map {field_map_id}")
            
            # Update the file with the field map
            update_file_field_map(file_id, field_map_id)
            
            # After successfully updating the field map, trigger transaction processing
            logger.info(f"Triggering transaction processing for file {file_id}")
            # Get the file content from S3
            s3_key = file.s3_key
            if not s3_key:
                logger.warning(f"File {file_id} has no S3 key, skipping transaction processing")
                return create_response(200, {
                    "message": "File successfully associated with field map",
                    "fileId": file_id,
                    "fieldMapId": field_map_id,
                    "fieldMapName": field_map.get('name')
                })
            
            # Get file content from S3
            content_bytes = get_object_content(s3_key)
            if content_bytes is None:
                return create_response(500, {"message": "Error reading file content"})
            
            # Get file format
            file_format = FileFormat(file.file_format)
            
            # Get opening balance if exists
            opening_balance = float(file.opening_balance) if file.opening_balance else None
            
            # Process transactions with new field map
            result = process_file_with_account(
                file_id, 
                content_bytes, 
                file_format, 
                opening_balance,
                user['id']
            )
            
            if isinstance(result, dict) and 'body' in result:
                try:
                    result_body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
                    transaction_count = result_body.get('transactionCount', 0)
                except (json.JSONDecodeError, AttributeError):
                    transaction_count = 0
            else:
                transaction_count = 0

            return create_response(200, {
                "message": "File successfully associated with field map and transactions processed",
                "fileId": file_id,
                "fieldMapId": field_map_id,
                "fieldMapName": field_map.get('name'),
                "transactionCount": transaction_count
            })
            
        except Exception as e:
            logger.error(f"Error updating file: {str(e)}")
            return create_response(500, {"message": "Error updating file"})
            
    except ValueError as e:
        return create_response(400, {"message": str(e)})
    except Exception as e:
        logger.error(f"Error updating file field map: {str(e)}")
        return create_response(500, {"message": "Error updating file field map"})

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for file operations."""
    logger.info(f"Processing request with event: {json.dumps(event)}")
    
    # Handle preflight OPTIONS request
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return create_response(200, {"message": "OK"})
    
    # Extract user information
    user = get_user_from_event(event)
    if not user:
        logger.error("No user found in token")
        return create_response(401, {"message": "Unauthorized"})
    
    # Get the HTTP method and route
    method = event.get("requestContext", {}).get("http", {}).get("method", "").upper()
    route = event.get("routeKey", "")
    
    # Log request details
    logger.info(f"Request: {method} {route}")
    
    # Handle based on route
    if route == "GET /files":
        return list_files_handler(event, user)
    elif route == "GET /files/account/{accountId}":
        return get_files_by_account_handler(event, user)
    elif route == "POST /files/upload":
        return get_upload_url_handler(event, user)
    elif route == "GET /files/{id}/metadata":
        return get_file_metadata_handler(event, user)
    elif route == "GET /files/{id}/content":
        return get_file_content_handler(event, user)
    elif route == "GET /files/{id}/download":
        return get_download_url_handler(event, user)
    elif route == "GET /files/{id}/transactions":
        return get_file_transactions_handler(event, user)
    elif route == "DELETE /files/{id}/transactions":
        return delete_file_transactions_handler(event, user)
    elif route == "DELETE /files/{id}":
        return delete_file_handler(event, user)
    elif route == "POST /files/{id}/unassociate":
        return unassociate_file_handler(event, user)
    elif route == "POST /files/{id}/associate":
        return associate_file_handler(event, user)
    elif route == "POST /files/{id}/balance":
        return update_file_balance_handler(event, user)
    elif route == "PUT /files/{id}/field-map":
        return update_file_field_map_handler(event, user)
    else:
        return create_response(400, {"message": f"Unsupported route: {route}"}) 