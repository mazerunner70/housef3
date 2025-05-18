import json
import logging
import os
import traceback
import uuid
from models.money import Currency, Money
from services.file_processor_service import FileProcessorResponse
from utils.db_utils import (
    get_file_map, 
    get_transaction_file, 
    list_user_files, 
    list_account_files, 
    create_transaction_file, 
    update_account, 
    update_file_field_map, 
    update_transaction_file, 
    delete_file_metadata, 
    get_account, 
    list_file_transactions, 
    delete_transactions_for_file, 
    get_file_maps_table,
    checked_mandatory_account,
    checked_mandatory_transaction_file,
    checked_optional_account,
    NotFound
)
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal
from models.transaction_file import FileFormat, ProcessingStatus, DateRange, validate_transaction_file_data, transaction_file_to_json
from models.transaction import Transaction
from utils.transaction_parser import file_type_selector, parse_transactions
from utils.s3_dao import (
    get_presigned_post_url,
    delete_object,
    get_object_content,
    get_presigned_url_simple,
    put_object
)
from handlers.file_processor import process_file
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
    """Generate a presigned URL for direct S3 upload without creating metadata."""
    try:
        # Parse request body
        key = mandatory_body_parameter(event, 'key')
        content_type = mandatory_body_parameter(event, 'contentType')
        account_id = optional_body_parameter(event, 'accountId')
        
        # Validate the key starts with the user's ID for security
        if not key.startswith(f"{user['id']}/"):
            return create_response(403, {'message': 'Invalid key prefix'})
            
        # If account_id is provided, verify user has access to it
        if account_id:
            try:
                checked_mandatory_account(account_id, user['id'])
            except ValueError as e:
                return create_response(403, {'message': str(e)})
            
        # Prepare fields for presigned URL
        fields = {}
        
        # Define policy conditions using consistent format
        conditions = [
            ['starts-with', '$Content-Type', ''],
            ['starts-with', '$key', f"{user['id']}/"]  # Ensure key starts with user ID
        ]
        
        # If account_id is provided, explicitly allow it in the policy
        if account_id:
            # Add the x-amz-meta-accountid field to allowed fields
            # Use the AWS-documented format for metadata fields in S3 policies
            fields['x-amz-meta-accountid'] = account_id
            # AWS requires explicit condition for each metadata field in POST policy
            conditions.append(['eq', '$x-amz-meta-accountid', account_id])
            
        # Log the complete conditions and fields for debugging
        logger.info(f"S3 policy conditions: {json.dumps(conditions)}")
        logger.info(f"S3 policy fields: {json.dumps(fields)}")
            
        # Get presigned post data with all fields pre-populated
        presigned_data = get_presigned_post_url(
            FILE_STORAGE_BUCKET, 
            key, 
            3600,
            conditions=conditions,
            fields=fields
        )
        
        # Add content type to fields to ensure it's sent correctly
        if 'fields' in presigned_data:
            presigned_data['fields']['Content-Type'] = content_type
        
        # Extract file ID from key (format: userId/fileId/filename)
        file_id = key.split('/')[1]
        
        logger.info(f"Generated presigned URL data: {json.dumps(presigned_data)}")
        
        return create_response(200, {
            'url': presigned_data['url'],
            'fields': presigned_data['fields'],
            'fileId': file_id,
            'expires': 3600  # URL expires in 1 hour
        })
    except ValueError as ve:
        return handle_error(400, str(ve))
    except Exception as e:
        logger.error(f"Error generating S3 upload URL: {str(e)}")
        return handle_error(500, "Error generating S3 upload URL")


def get_download_url_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a presigned URL for file download."""
    try:
        # Get file ID from path parameters
        file_id = mandatory_path_parameter(event, 'id')
            
        # Get file metadata from DynamoDB
        file = checked_mandatory_transaction_file(file_id, user['id'])
    
        # Generate presigned URL for download
        download_url = get_presigned_url_simple(FILE_STORAGE_BUCKET, file.s3_key, 'get')
        
        return create_response(200, {
            'fileId': file.file_id,
            'downloadUrl': download_url,
            'fileName': file.file_name,
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
        file = checked_mandatory_transaction_file(file_id, user['id'])
            
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
        file = checked_mandatory_transaction_file(file_id, user['id'])
        
        # Check if file is associated with an account
        if not file.account_id:
            raise ValueError("File is not associated with any account")
        
        checked_mandatory_account(file.account_id, user['id'])
        
        # Update the file to remove account association
        logger.info(f"Removing association between file {file_id} and account {file.account_id}")
        update_transaction_file(file_id, user['id'], {'account_id': None})          
        return create_response(200, {
            "message": "File successfully unassociated from account",
            "fileId": file_id,
            "previousAccountId": file.account_id
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
        file = checked_mandatory_transaction_file(file_id, user['id'])
                 
        # Verify that the account exists and belongs to the user
        account = checked_mandatory_account(account_id, user['id'])
            
        # Update the file to add account association
        logger.info(f"Associating file {file_id} with account {account_id}")
        file.account_id = account_id
        response: FileProcessorResponse = process_file(file)
        return create_response(200, response.to_dict())
    except Exception as e:
        logger.error(f"Error associating file: {str(e)}")
        return create_response(500, {"message": "Error handling associate request"})

def update_file_balance_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Update a file's opening balance."""
    try:
        # Get file ID from path parameters
        file_id = mandatory_path_parameter(event, 'id')
            
        # Get file metadata from DynamoDB
        file = checked_mandatory_transaction_file(file_id, user['id'])
        
        # Parse the request body to get the opening balance
        amount = Decimal(mandatory_body_parameter(event, 'amount'))
        currency = mandatory_body_parameter(event, 'currency')
        opening_balance = Money(amount, Currency(currency))
        file.opening_balance = opening_balance
        response: FileProcessorResponse = process_file(file)

        return create_response(200, response.to_dict())

    except ValueError as e: 
        logger.error(f"Error updating file balance: {str(e)}")
        logger.error(traceback.format_exc())
        return handle_error(400, str(e))
    except NotFound as e:
        logger.error(f"File not found: {str(e)}")
        logger.error(traceback.format_exc())
        return handle_error(404, str(e))
    except Exception as e:
        logger.error(f"Error updating file balance: {str(e)}")
        logger.error(traceback.format_exc())
        return create_response(500, {"message": "Error handling update balance request"})

def get_file_metadata_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Get metadata for a single file by ID."""
    try:
        # Get file ID from path parameters
        file_id = mandatory_path_parameter(event, 'id') 
        
        # Get file metadata from DynamoDB
        file = checked_mandatory_transaction_file(file_id, user['id'])
        
        # Convert to JSON-friendly format with proper type handling
        file_json = json.loads(transaction_file_to_json(file))
        
        # Add field map information if it exists
        if 'fieldMapId' in file_json:
            field_map = get_file_map(file_json['fieldMapId'])
            if field_map:
                file_json['fieldMap'] = {
                    'fieldMapId': field_map.file_map_id,
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
        file = checked_mandatory_transaction_file(file_id, user['id'])
        
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
        file = checked_mandatory_transaction_file(file_id, user['id'])
        
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
        file = checked_mandatory_transaction_file(file_id, user['id'])
        
        # Get the file content from S3 using S3 DAO
        content = get_object_content(file.s3_key)
        if content is None:
            return create_response(500, {"message": "Error reading file content"})
            
        return create_response(200, {
            'fileId': file_id,
            'content': content.decode('utf-8'),
            'contentType': file.file_format.value if file.file_format else 'unknown',
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
        
        # Get the field map ID from the request body
        field_map_id = mandatory_body_parameter(event, 'fileMapId')
            
        # Get file metadata from DynamoDB
        file = checked_mandatory_transaction_file(file_id, user['id'])
        
        # Get field map
        field_map = get_file_map(field_map_id)
        if not field_map:
            return create_response(404, {"message": "Field map not found"})
        file.file_map_id = field_map_id
        response: FileProcessorResponse = process_file(file)
        return create_response(200, response.to_dict())
                    
    except ValueError as e:
        logger.error(f"Validation error in update_file_field_map_handler: {str(e)}", exc_info=True)
        return create_response(400, {"message": str(e)})
    except Exception as e:
        logger.error(f"Error updating file field map: {str(e)}", exc_info=True)
        return create_response(500, {"message": "Error updating file field map"})

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for file operations."""
    try:
        # Get route from event
        route = event.get('routeKey')
        if not route:
            return create_response(400, {"message": "Missing route key"})
            
        # Get user from event
        user = get_user_from_event(event)
        if not user:
            return create_response(401, {"message": "Unauthorized"})
            
        logger.info(f"Processing {route} request for user {user.get('id')}")
        
        # Handle based on route
        if route == "GET /files":
            return list_files_handler(event, user)
        elif route == "GET /files/account/{accountId}":
            return get_files_by_account_handler(event, user)
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
        elif route == "PUT /files/{id}/file-map":
            return update_file_field_map_handler(event, user)
        elif route == "POST /files/upload":
            return get_upload_url_handler(event, user)
        else:
            return create_response(400, {"message": f"Unsupported route: {route}"})
    except Exception as e:
        logger.error(f"Error in handler: {str(e)}")
        return create_response(500, {"message": "Internal server error"}) 