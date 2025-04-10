import json
import logging
import os
import uuid
import boto3
from datetime import datetime
from typing import Dict, Any, List, Optional
from decimal import Decimal

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
    from models.account import Account, AccountType, Currency, validate_account_data
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
        from ..models.account import Account, AccountType, Currency, validate_account_data
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
            return float(obj) if obj % 1 else int(obj)
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

def create_account_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new financial account."""
    try:
        # Parse the request body
        body = json.loads(event.get('body', '{}'))
        
        # Add user ID to the account data
        body['userId'] = user['id']
        
        # Convert string values to enum types
        if 'accountType' in body and isinstance(body['accountType'], str):
            body['accountType'] = AccountType(body['accountType'])
            
        if 'currency' in body and isinstance(body['currency'], str):
            body['currency'] = Currency(body['currency'])
        
        # Validate and create the account
        account = create_account(body)
        
        # Return the created account
        account_dict = account.to_dict()
        
        return create_response(201, {
            'message': 'Account created successfully',
            'account': account_dict
        })
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return create_response(400, {"message": str(e)})
    except Exception as e:
        logger.error(f"Error creating account: {str(e)}")
        return create_response(500, {"message": "Error creating account"})

def get_account_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Get a specific account by ID."""
    try:
        # Get account ID from path parameters
        account_id = event.get('pathParameters', {}).get('id')
        
        if not account_id:
            return create_response(400, {"message": "Account ID is required"})
        
        # Get the account
        account = get_account(account_id)
        
        if not account:
            return create_response(404, {"message": f"Account not found: {account_id}"})
        
        # Verify user ownership
        if account.user_id != user['id']:
            return create_response(403, {"message": "Access denied"})
        
        # Convert account to dictionary
        account_dict = account.to_dict()
        
        return create_response(200, {
            'account': account_dict
        })
    except Exception as e:
        logger.error(f"Error getting account: {str(e)}")
        return create_response(500, {"message": "Error retrieving account"})

def list_accounts_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """List all accounts for the current user."""
    try:
        # Get query parameters for filtering/sorting (if implemented)
        query_params = event.get('queryStringParameters', {}) or {}
        
        # Get accounts for the user
        accounts = list_user_accounts(user['id'])
        
        # Convert accounts to dictionary format
        account_dicts = [account.to_dict() for account in accounts]
        
        return create_response(200, {
            'accounts': account_dicts,
            'user': user,
            'metadata': {
                'totalAccounts': len(account_dicts)
            }
        })
    except Exception as e:
        logger.error(f"Error listing accounts: {str(e)}")
        return create_response(500, {"message": "Error listing accounts"})

def update_account_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing account."""
    try:
        # Get account ID from path parameters
        account_id = event.get('pathParameters', {}).get('id')
        
        if not account_id:
            return create_response(400, {"message": "Account ID is required"})
        
        # Parse the request body
        body = json.loads(event.get('body', '{}'))
        
        # Convert string values to enum types
        if 'accountType' in body and isinstance(body['accountType'], str):
            body['accountType'] = AccountType(body['accountType'])
            
        if 'currency' in body and isinstance(body['currency'], str):
            body['currency'] = Currency(body['currency'])
        
        # Verify the account exists and belongs to the user
        existing_account = get_account(account_id)
        
        if not existing_account:
            return create_response(404, {"message": f"Account not found: {account_id}"})
        
        if existing_account.user_id != user['id']:
            return create_response(403, {"message": "Access denied"})
        
        # Update the account
        updated_account = update_account(account_id, body)
        
        # Return the updated account
        account_dict = updated_account.to_dict()
        
        return create_response(200, {
            'message': 'Account updated successfully',
            'account': account_dict
        })
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return create_response(400, {"message": str(e)})
    except Exception as e:
        logger.error(f"Error updating account: {str(e)}")
        return create_response(500, {"message": "Error updating account"})

def delete_account_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Delete an account."""
    try:
        # Get account ID from path parameters
        account_id = event.get('pathParameters', {}).get('id')
        
        if not account_id:
            return create_response(400, {"message": "Account ID is required"})
        
        # Verify the account exists and belongs to the user
        existing_account = get_account(account_id)
        
        if not existing_account:
            return create_response(404, {"message": f"Account not found: {account_id}"})
        
        if existing_account.user_id != user['id']:
            return create_response(403, {"message": "Access denied"})
        
        # Delete the account
        delete_account(account_id)
        
        return create_response(200, {
            'message': 'Account deleted successfully',
            'accountId': account_id
        })
    except Exception as e:
        logger.error(f"Error deleting account: {str(e)}")
        return create_response(500, {"message": "Error deleting account"})

def account_files_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """List all files associated with an account."""
    try:
        # Get account ID from path parameters
        account_id = event.get('pathParameters', {}).get('id')
        
        if not account_id:
            return create_response(400, {"message": "Account ID is required"})
        
        # Verify the account exists and belongs to the user
        existing_account = get_account(account_id)
        
        if not existing_account:
            return create_response(404, {"message": f"Account not found: {account_id}"})
        
        if existing_account.user_id != user['id']:
            return create_response(403, {"message": "Access denied"})
        
        # Get files for the account
        files = list_account_files(account_id)
        
        # Convert files to dictionary format
        file_dicts = [file.to_dict() for file in files]
        
        return create_response(200, {
            'files': file_dicts,
            'user': user,
            'metadata': {
                'totalFiles': len(file_dicts),
                'accountId': account_id,
                'accountName': existing_account.account_name
            }
        })
    except Exception as e:
        logger.error(f"Error listing account files: {str(e)}")
        return create_response(500, {"message": "Error listing account files"})

def account_file_upload_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Create a pre-signed URL for uploading a file to S3 and associate it with an account."""
    try:
        # Get account ID from path parameters
        account_id = event.get('pathParameters', {}).get('id')
        
        if not account_id:
            return create_response(400, {"message": "Account ID is required"})
        
        # Verify the account exists and belongs to the user
        existing_account = get_account(account_id)
        
        if not existing_account:
            return create_response(404, {"message": f"Account not found: {account_id}"})
        
        if existing_account.user_id != user['id']:
            return create_response(403, {"message": "Access denied"})
        
        # Parse the request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        required_fields = ['fileName', 'contentType', 'fileSize']
        for field in required_fields:
            if field not in body:
                return create_response(400, {"message": f"Missing required field: {field}"})
        
        # Generate a unique file ID
        file_id = str(uuid.uuid4())
        
        # Get bucket name from environment variables
        bucket_name = os.environ.get('FILE_STORAGE_BUCKET')
        if not bucket_name:
            logger.error("FILE_STORAGE_BUCKET environment variable not set")
            return create_response(500, {"message": "Server configuration error"})
        
        # Create S3 client
        s3_client = boto3.client('s3')
        
        # Generate a key path based on user ID, account ID and file ID
        s3_key = f"{user['id']}/{file_id}/{body['fileName']}"
        
        # Generate a pre-signed URL for uploading the file
        expires_in = 3600  # URL expires in 1 hour
        try:
            upload_url = s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': bucket_name,
                    'Key': s3_key,
                    'ContentType': body['contentType']
                },
                ExpiresIn=expires_in
            )
        except Exception as e:
            logger.error(f"Error generating pre-signed URL: {str(e)}")
            return create_response(500, {"message": "Error generating upload URL"})
        
        # Determine file format based on filename or content type
        file_format = FileFormat.OTHER
        if 'fileFormat' in body:
            file_format = FileFormat(body['fileFormat'])
        elif body['fileName'].lower().endswith(('.csv')):
            file_format = FileFormat.CSV
        elif body['fileName'].lower().endswith(('.ofx', '.qfx')):
            file_format = FileFormat.OFX
        elif body['fileName'].lower().endswith('.pdf'):
            file_format = FileFormat.PDF
        elif body['fileName'].lower().endswith('.xlsx'):
            file_format = FileFormat.XLSX
        
        # Create transaction file record in DynamoDB
        try:
            file_data = {
                'fileId': file_id,
                'userId': user['id'],
                'accountId': account_id,
                'fileName': body['fileName'],
                'contentType': body['contentType'],
                'fileSize': body['fileSize'],
                'fileFormat': file_format.value,
                's3Key': s3_key,
                'processingStatus': ProcessingStatus.PENDING.value
            }
            
            transaction_file = create_transaction_file(file_data)
            
            # Return the response with file information and upload URL
            response = {
                'fileId': file_id,
                'uploadUrl': upload_url,
                'fileName': body['fileName'],
                'contentType': body['contentType'],
                'expires': expires_in,
                'processingStatus': 'pending',
                'fileFormat': file_format.value,
                'accountId': account_id
            }
            
            return create_response(201, response)
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return create_response(400, {"message": str(e)})
        except Exception as e:
            logger.error(f"Error creating file record: {str(e)}")
            return create_response(500, {"message": "Error creating file record"})
    except Exception as e:
        logger.error(f"Error processing file upload: {str(e)}")
        return create_response(500, {"message": "Error processing file upload request"})

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for account operations."""
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
    if route == "POST /accounts":
        return create_account_handler(event, user)
    elif route == "GET /accounts":
        return list_accounts_handler(event, user)
    elif route == "GET /accounts/{id}":
        return get_account_handler(event, user)
    elif route == "PUT /accounts/{id}":
        return update_account_handler(event, user)
    elif route == "DELETE /accounts/{id}":
        return delete_account_handler(event, user)
    elif route == "GET /accounts/{id}/files":
        return account_files_handler(event, user)
    elif route == "POST /accounts/{id}/files":
        return account_file_upload_handler(event, user)
    else:
        return create_response(400, {"message": f"Unsupported route: {route}"}) 