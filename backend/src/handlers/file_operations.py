import json
import logging
import os
import uuid
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
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
    from models.transaction_file import TransactionFile, FileFormat, ProcessingStatus, DateRange, validate_transaction_file_data
    from utils.db_utils import get_transaction_file, list_user_files, list_account_files, create_transaction_file, update_transaction_file, delete_transaction_file
    
    logger.info("Successfully imported modules using adjusted path")
except ImportError as e:
    logger.error(f"Import error: {str(e)}")
    # Log the current sys.path to debug import issues
    logger.error(f"Current sys.path: {sys.path}")
    # Last resort, try relative import
    try:
        from ..models.transaction_file import TransactionFile, FileFormat, ProcessingStatus, DateRange, validate_transaction_file_data
        from ..utils.db_utils import get_transaction_file, list_user_files, list_account_files, create_transaction_file, update_transaction_file, delete_transaction_file
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

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Get environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
FILE_STORAGE_BUCKET = os.environ.get('FILE_STORAGE_BUCKET')
FILES_TABLE = os.environ.get('FILES_TABLE')

# Initialize table resource
file_table = dynamodb.Table(FILES_TABLE)

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

def generate_file_id() -> str:
    """Generate a unique file ID."""
    return str(uuid.uuid4())

def get_presigned_url(bucket: str, key: str, operation: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for S3 operations."""
    try:
        if operation.lower() == 'put':
            return s3_client.generate_presigned_url(
                'put_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expires_in
            )
        elif operation.lower() == 'get':
            return s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expires_in
            )
        else:
            raise ValueError(f"Unsupported operation: {operation}")
    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}")
        raise

def list_files_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """List files for the current user."""
    try:
        # Log user details for debugging
        logger.info(f"Listing files for user: {user['id']}")
        
        # Check if there's an accountId filter
        query_params = event.get('queryStringParameters', {}) or {}
        account_id = query_params.get('accountId')
        
        files = []
        
        # If accountId provided, query by accountId
        if account_id:
            logger.info(f"Filtering files for account: {account_id}")
            try:
                response = file_table.query(
                    IndexName='AccountIdIndex',
                    KeyConditionExpression=boto3.dynamodb.conditions.Key('accountId').eq(account_id)
                )
                files = response.get('Items', [])
                logger.info(f"Found {len(files)} files for account {account_id}")
            except Exception as query_error:
                logger.error(f"Error querying AccountIdIndex: {str(query_error)}. Exception type: {type(query_error).__name__}")
        else:
            # First try using UserIndex GSI
            try:
                logger.info(f"Attempting to query UserIndex GSI for user: {user['id']}")
                
                # Query DynamoDB for user's files
                response = file_table.query(
                    IndexName='UserIndex',
                    KeyConditionExpression=boto3.dynamodb.conditions.Key('userId').eq(user['id'])
                )
                
                files = response.get('Items', [])
                logger.info(f"Query successful: Found {len(files)} files for user {user['id']} using GSI")
                
            except Exception as query_error:
                logger.error(f"Error querying UserIndex: {str(query_error)}. Exception type: {type(query_error).__name__}")
            
            # If GSI query returned no results or failed, fallback to scan
            if not files:
                logger.info(f"No files found with GSI or GSI query failed. Trying scan as fallback for user: {user['id']}")
                
                try:
                    # Fallback to scan with filter
                    scan_response = file_table.scan(
                        FilterExpression=boto3.dynamodb.conditions.Attr('userId').eq(user['id'])
                    )
                    
                    files = scan_response.get('Items', [])
                    logger.info(f"Fallback scan found {len(files)} files for user {user['id']}")
                    
                    if files:
                        logger.info(f"First file from scan: {json.dumps(files[0])}")
                except Exception as scan_error:
                    logger.error(f"Error in fallback scan: {str(scan_error)}. Exception type: {type(scan_error).__name__}")
        
        # Convert DynamoDB response to more user-friendly format
        formatted_files = []
        for file in files:
            formatted_file = {
                'fileId': file.get('fileId'),
                'fileName': file.get('fileName'),
                'contentType': file.get('contentType'),
                'fileSize': file.get('fileSize'),
                'uploadDate': file.get('uploadDate'),
                'lastModified': file.get('lastModified', file.get('uploadDate'))
            }
            
            # Include TransactionFile model specific fields if they exist
            if 'accountId' in file:
                formatted_file['accountId'] = file.get('accountId')
            
            if 'fileFormat' in file:
                formatted_file['fileFormat'] = file.get('fileFormat')
                
            if 'processingStatus' in file:
                formatted_file['processingStatus'] = file.get('processingStatus')
                
            if 'recordCount' in file:
                formatted_file['recordCount'] = file.get('recordCount')
                
            if 'dateRange' in file:
                formatted_file['dateRange'] = file.get('dateRange')
                
            if 'errorMessage' in file:
                formatted_file['errorMessage'] = file.get('errorMessage')
            
            formatted_files.append(formatted_file)
            
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
    """List files for a specific account."""
    try:
        # Get account ID from path parameters
        account_id = event.get('pathParameters', {}).get('accountId')
        
        if not account_id:
            return create_response(400, {"message": "Account ID is required"})
            
        logger.info(f"Listing files for account: {account_id}")
        
        # Query DynamoDB for account's files
        try:
            response = file_table.query(
                IndexName='AccountIdIndex',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('accountId').eq(account_id)
            )
            
            files = response.get('Items', [])
            logger.info(f"Found {len(files)} files for account {account_id}")
            
            # Convert DynamoDB response to more user-friendly format
            formatted_files = []
            for file in files:
                formatted_file = {
                    'fileId': file.get('fileId'),
                    'fileName': file.get('fileName'),
                    'contentType': file.get('contentType'),
                    'fileSize': file.get('fileSize'),
                    'uploadDate': file.get('uploadDate'),
                    'lastModified': file.get('lastModified', file.get('uploadDate')),
                    'accountId': file.get('accountId')
                }
                
                # Include TransactionFile model specific fields if they exist
                if 'fileFormat' in file:
                    formatted_file['fileFormat'] = file.get('fileFormat')
                    
                if 'processingStatus' in file:
                    formatted_file['processingStatus'] = file.get('processingStatus')
                    
                if 'recordCount' in file:
                    formatted_file['recordCount'] = file.get('recordCount')
                    
                if 'dateRange' in file:
                    formatted_file['dateRange'] = file.get('dateRange')
                    
                if 'errorMessage' in file:
                    formatted_file['errorMessage'] = file.get('errorMessage')
                
                formatted_files.append(formatted_file)
                
            return create_response(200, {
                'files': formatted_files,
                'user': user,
                'metadata': {
                    'totalFiles': len(formatted_files),
                    'timestamp': datetime.utcnow().isoformat(),
                    'accountId': account_id
                }
            })
                
        except Exception as query_error:
            logger.error(f"Error querying AccountIdIndex: {str(query_error)}. Exception type: {type(query_error).__name__}")
            return create_response(500, {"message": "Error listing files for account"})
            
    except Exception as e:
        logger.error(f"Error listing files for account: {str(e)}, Exception type: {type(e).__name__}")
        return create_response(500, {"message": "Error listing files for account"})

def get_upload_url_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a presigned URL for file upload."""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        file_name = body.get('fileName')
        content_type = body.get('contentType', 'text/plain')
        file_size = body.get('fileSize', 0)
        account_id = body.get('accountId')
        
        if not file_name:
            return create_response(400, {"message": "fileName is required"})
        
        # Validate account_id if it's a transaction file
        if account_id:
            if not account_id.strip():
                return create_response(400, {"message": "accountId cannot be empty if provided"})
        else:
            # If not associated with an account, it's a regular file
            pass
            
        # Generate a unique file ID
        file_id = generate_file_id()
        
        # Use user ID as part of the key for organization
        file_key = f"{user['id']}/{file_id}/{file_name}"
        
        # Generate presigned URL for upload
        upload_url = get_presigned_url(FILE_STORAGE_BUCKET, file_key, 'put')
        
        # Determine file format based on content type or file extension
        file_format = determine_file_format(file_name, content_type)
        
        # Store file metadata in DynamoDB
        current_time = datetime.utcnow().isoformat()
        
        # Create basic item with required fields
        item = {
            'fileId': file_id,
            'userId': user['id'],
            'fileName': file_name,
            'contentType': content_type,
            'fileSize': file_size,
            'uploadDate': current_time,
            'lastModified': current_time,
            's3Key': file_key,
            'processingStatus': ProcessingStatus.PENDING.value,
            'fileFormat': file_format.value
        }
        
        # Add accountId if provided (for transaction files)
        if account_id:
            item['accountId'] = account_id
        
        logger.info(f"Saving file metadata to DynamoDB: {json.dumps(item)}")
        logger.info(f"User ID for index: {user['id']}")
        
        file_table.put_item(Item=item)
        
        # Create response with basic fields
        response = {
            'fileId': file_id,
            'uploadUrl': upload_url,
            'fileName': file_name,
            'contentType': content_type,
            'expires': 3600,  # URL expires in 1 hour
            'processingStatus': ProcessingStatus.PENDING.value,
            'fileFormat': file_format.value
        }
        
        # Include accountId in response if it was provided
        if account_id:
            response['accountId'] = account_id
            
        return create_response(200, response)
    except Exception as e:
        logger.error(f"Error generating upload URL: {str(e)}, Exception type: {type(e).__name__}")
        return create_response(500, {"message": "Error generating upload URL"})

def determine_file_format(file_name: str, content_type: str) -> FileFormat:
    """Determine the file format based on file name and content type."""
    # Extract extension from file name
    extension = file_name.split('.')[-1].lower() if '.' in file_name else ''
    
    # Map extensions to FileFormat enum
    extension_map = {
        'csv': FileFormat.CSV,
        'ofx': FileFormat.OFX,
        'qfx': FileFormat.QFX,
        'pdf': FileFormat.PDF,
        'xlsx': FileFormat.XLSX
    }
    
    # Content type mapping
    content_type_map = {
        'text/csv': FileFormat.CSV,
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': FileFormat.XLSX,
        'application/pdf': FileFormat.PDF
    }
    
    # Try to determine by extension first
    if extension in extension_map:
        return extension_map[extension]
    
    # If not successful, try by content type
    if content_type in content_type_map:
        return content_type_map[content_type]
    
    # Default to OTHER if we can't determine
    return FileFormat.OTHER

def get_download_url_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a presigned URL for file download."""
    try:
        # Get file ID from path parameters
        file_id = event.get('pathParameters', {}).get('id')
        
        if not file_id:
            return create_response(400, {"message": "File ID is required"})
            
        # Get file metadata from DynamoDB
        response = file_table.get_item(Key={'fileId': file_id})
        file = response.get('Item')
        
        if not file:
            return create_response(404, {"message": "File not found"})
            
        # Check if the file belongs to the user
        if file.get('userId') != user['id']:
            return create_response(403, {"message": "Access denied"})
            
        # Generate presigned URL for download
        download_url = get_presigned_url(FILE_STORAGE_BUCKET, file.get('s3Key'), 'get')
        
        return create_response(200, {
            'fileId': file_id,
            'downloadUrl': download_url,
            'fileName': file.get('fileName'),
            'contentType': file.get('contentType'),
            'expires': 3600  # URL expires in 1 hour
        })
    except Exception as e:
        logger.error(f"Error generating download URL: {str(e)}")
        return create_response(500, {"message": "Error generating download URL"})

def delete_file_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Delete a file."""
    try:
        # Get file ID from path parameters
        file_id = event.get('pathParameters', {}).get('id')
        
        if not file_id:
            return create_response(400, {"message": "File ID is required"})
            
        # Get file metadata from DynamoDB
        response = file_table.get_item(Key={'fileId': file_id})
        file = response.get('Item')
        
        if not file:
            return create_response(404, {"message": "File not found"})
            
        # Check if the file belongs to the user
        if file.get('userId') != user['id']:
            return create_response(403, {"message": "Access denied"})
            
        # Delete file from S3
        s3_client.delete_object(
            Bucket=FILE_STORAGE_BUCKET,
            Key=file.get('s3Key')
        )
        
        # Delete metadata from DynamoDB
        file_table.delete_item(Key={'fileId': file_id})
        
        return create_response(200, {
            'message': 'File deleted successfully',
            'fileId': file_id
        })
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return create_response(500, {"message": "Error deleting file"})

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
    elif route == "GET /files/{id}/download":
        return get_download_url_handler(event, user)
    elif route == "DELETE /files/{id}":
        return delete_file_handler(event, user)
    else:
        return create_response(400, {"message": f"Unsupported route: {route}"}) 