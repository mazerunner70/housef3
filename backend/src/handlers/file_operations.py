import json
import logging
import os
import uuid
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal
from models.transaction_file import FileFormat, ProcessingStatus
from models.transaction import Transaction
from utils.db_utils import get_transaction_file, list_user_files, list_account_files, create_transaction_file, update_transaction_file, delete_file_metadata, get_account, list_file_transactions, delete_transactions_for_file
from utils.transaction_parser import process_file_transactions

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
FILE_STORAGE_BUCKET = os.environ.get('FILE_STORAGE_BUCKET', 'housef3-dev-file-storage')
FILES_TABLE = os.environ.get('FILES_TABLE')

if not FILE_STORAGE_BUCKET:
    logger.error("FILE_STORAGE_BUCKET environment variable not set")
    raise ValueError("FILE_STORAGE_BUCKET environment variable not set")

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
        if not isinstance(bucket, str) or not bucket:
            raise ValueError("Bucket name must be a non-empty string")
            
        if not isinstance(key, str) or not key:
            raise ValueError("Key must be a non-empty string")
            
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
            
            if 'openingBalance' in file:
                formatted_file['openingBalance'] = float(file.get('openingBalance'))
            
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
        
        # Verify the account exists and belongs to the user
        account = get_account(account_id)
        if not account:
            return create_response(404, {"message": f"Account not found: {account_id}"})
        
        if account.user_id != user['id']:
            return create_response(403, {"message": "Access denied. You do not own this account"})
            
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
                
                if 'openingBalance' in file:
                    formatted_file['openingBalance'] = float(file.get('openingBalance'))
                
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
        
        # Validate account_id if it's provided (for account-file association)
        if account_id:
            if not account_id.strip():
                return create_response(400, {"message": "accountId cannot be empty if provided"})
            
            # Verify the account exists and belongs to the user
            account = get_account(account_id)
            if not account:
                return create_response(404, {"message": f"Account not found: {account_id}"})
            
            if account.user_id != user['id']:
                return create_response(403, {"message": "Access denied. You do not own this account"})
            
            logger.info(f"Associating file with account: {account_id}")
        else:
            # If not associated with an account, it's a standalone file
            logger.info("Creating a standalone file (no account association)")
            
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
        
        # Check if file is associated with an account
        account_id = None
        if 'accountId' in file:
            account_id = file.get('accountId')
            logger.info(f"File {file_id} is associated with account {account_id}. This association will be removed during deletion.")
            
        # Delete file from S3
        try:
            s3_client.delete_object(
                Bucket=FILE_STORAGE_BUCKET,
                Key=file.get('s3Key')
            )
            logger.info(f"Successfully deleted file {file_id} from S3 bucket {FILE_STORAGE_BUCKET}")
        except Exception as s3_error:
            logger.error(f"Error deleting file from S3: {str(s3_error)}")
            return create_response(500, {"message": "Error deleting file from S3"})
        
        # Delete metadata from DynamoDB
        try:
            file_table.delete_item(Key={'fileId': file_id})
            logger.info(f"Successfully deleted file {file_id} from DynamoDB table")
            
            # Verify the file is deleted
            verification = file_table.get_item(Key={'fileId': file_id})
            if 'Item' in verification:
                logger.error(f"File {file_id} was not deleted from DynamoDB")
                return create_response(500, {"message": "Error verifying file deletion"})
                
            # If file was associated with an account, verify it's removed from the index
            if account_id:
                # Check if the file still appears in the account's files
                verification_query = file_table.query(
                    IndexName='AccountIdIndex',
                    KeyConditionExpression=boto3.dynamodb.conditions.Key('accountId').eq(account_id)
                )
                account_files = verification_query.get('Items', [])
                for account_file in account_files:
                    if account_file.get('fileId') == file_id:
                        logger.error(f"File {file_id} still appears in account {account_id} index")
                        # This should never happen if the main item is deleted
            
            logger.info(f"File {file_id} deletion verified")
            
        except Exception as dynamo_error:
            logger.error(f"Error deleting file from DynamoDB: {str(dynamo_error)}")
            return create_response(500, {"message": "Error deleting file metadata from database"})
        
        return create_response(200, {
            'message': 'File deleted successfully',
            'fileId': file_id
        })
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return create_response(500, {"message": "Error deleting file"})

def unassociate_file_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Remove account association from a file."""
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
        
        # Check if file is associated with an account
        if 'accountId' not in file:
            return create_response(400, {"message": "File is not associated with any account"})
        
        account_id = file.get('accountId')
        
        # Update the file to remove account association
        try:
            logger.info(f"Removing association between file {file_id} and account {account_id}")
            
            # Create update expression to remove accountId
            update_expression = "REMOVE accountId"
            
            # Update the file
            file_table.update_item(
                Key={'fileId': file_id},
                UpdateExpression=update_expression
            )
            
            return create_response(200, {
                "message": "File successfully unassociated from account",
                "fileId": file_id,
                "previousAccountId": account_id
            })
        except Exception as update_error:
            logger.error(f"Error updating file: {str(update_error)}")
            return create_response(500, {"message": "Error unassociating file from account"})
    except Exception as e:
        logger.error(f"Error unassociating file: {str(e)}")
        return create_response(500, {"message": "Error handling unassociate request"})

def associate_file_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Associate a file with an account."""
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
        
        # Check if file is already associated with an account
        if 'accountId' in file:
            return create_response(400, {"message": "File is already associated with an account"})
        
        # Parse the request body to get the account ID
        try:
            request_body = json.loads(event.get('body', '{}'))
            account_id = request_body.get('accountId')
            
            if not account_id:
                return create_response(400, {"message": "Account ID is required"})
        except Exception as parse_error:
            logger.error(f"Error parsing request body: {str(parse_error)}")
            return create_response(400, {"message": "Invalid request body"})
        
        # Verify that the account exists and belongs to the user
        try:
            account_response = get_account(account_id)
            
            if not account_response:
                return create_response(404, {"message": "Account not found"})
                
            # Check if the account belongs to the user
            if account_response.user_id != user['id']:
                return create_response(403, {"message": "Access denied to the specified account"})
        except Exception as account_error:
            logger.error(f"Error verifying account: {str(account_error)}")
            return create_response(500, {"message": "Error verifying account"})
        
        # Update the file to add account association
        try:
            logger.info(f"Associating file {file_id} with account {account_id}")
            
            # Create update expression to add accountId
            update_expression = "SET accountId = :accountId"
            expression_attribute_values = {
                ":accountId": account_id
            }
            
            # Update the file
            file_table.update_item(
                Key={'fileId': file_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            
            return create_response(200, {
                "message": "File successfully associated with account",
                "fileId": file_id,
                "accountId": account_id,
                "accountName": account_response.account_name
            })
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
        
        # Parse the request body to get the opening balance
        try:
            request_body = json.loads(event.get('body', '{}'))
            opening_balance = request_body.get('openingBalance')
            
            if opening_balance is None:
                return create_response(400, {"message": "Opening balance is required"})
                
            # Convert to proper type and validate
            try:
                opening_balance = float(opening_balance)
            except (ValueError, TypeError):
                return create_response(400, {"message": "Opening balance must be a valid number"})
        except Exception as parse_error:
            logger.error(f"Error parsing request body: {str(parse_error)}")
            return create_response(400, {"message": "Invalid request body"})
        
        # Update the file with the new opening balance
        try:
            logger.info(f"Updating opening balance for file {file_id} to {opening_balance}")
            
            # Create update expression to set opening balance
            update_expression = "SET openingBalance = :balance"
            expression_attribute_values = {
                ":balance": str(opening_balance)  # Convert to string for DynamoDB
            }
            
            # Update the file
            file_table.update_item(
                Key={'fileId': file_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            
            # After successfully updating the opening balance, trigger transaction reprocessing
            try:
                logger.info(f"Triggering transaction reprocessing for file {file_id}")
                # Get the file content from S3
                s3_key = file.get('s3Key')
                if not s3_key:
                    logger.warning(f"File {file_id} has no S3 key, skipping transaction processing")
                    return create_response(200, {
                        "message": "File opening balance updated successfully",
                        "fileId": file_id,
                        "openingBalance": opening_balance
                    })
                
                # Get file content from S3
                response = s3_client.get_object(Bucket=FILE_STORAGE_BUCKET, Key=s3_key)
                content_bytes = response['Body'].read()
                
                # Get file format
                file_format = FileFormat(file.get('fileFormat', 'other'))
                
                # Process transactions with new opening balance
                transaction_count = process_file_transactions(
                    file_id, 
                    content_bytes, 
                    file_format, 
                    opening_balance
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
        
        # Convert DynamoDB response to user-friendly format
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
        
        if 'openingBalance' in file:
            formatted_file['openingBalance'] = float(file.get('openingBalance'))
        
        return create_response(200, formatted_file)
    except Exception as e:
        logger.error(f"Error getting file metadata: {str(e)}")
        return create_response(500, {"message": "Error getting file metadata"})

def get_file_transactions_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Get all transactions for a specific file."""
    try:
        # Get file ID from path parameters
        file_id = event.get('pathParameters', {}).get('id')
        
        if not file_id:
            return create_response(400, {"message": "File ID is required"})
            
        # Get file metadata to verify ownership
        response = file_table.get_item(Key={'fileId': file_id})
        file = response.get('Item')
        
        if not file:
            return create_response(404, {"message": "File not found"})
            
        # Check if the file belongs to the user
        if file.get('userId') != user['id']:
            return create_response(403, {"message": "Access denied"})
        
        # Get transactions for the file
        try:
            transactions = list_file_transactions(file_id)
            
            # Format transactions for response
            formatted_transactions = []
            for transaction in transactions:
                formatted_transaction = {
                    'transactionId': transaction.get('transactionId'),
                    'date': transaction.get('date'),
                    'description': transaction.get('description'),
                    'amount': float(transaction.get('amount')),
                    'runningTotal': float(transaction.get('runningTotal')),
                    'transactionType': transaction.get('transactionType'),
                    'category': transaction.get('category'),
                    'memo': transaction.get('memo')
                }
                formatted_transactions.append(formatted_transaction)
            
            # Sort transactions by date
            formatted_transactions.sort(key=lambda x: x['date'])
            
            return create_response(200, {
                'fileId': file_id,
                'transactions': formatted_transactions,
                'metadata': {
                    'totalTransactions': len(formatted_transactions),
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
        file_id = event.get('pathParameters', {}).get('id')
        
        if not file_id:
            return create_response(400, {"message": "File ID is required"})
            
        # Get file metadata to verify ownership
        response = file_table.get_item(Key={'fileId': file_id})
        file = response.get('Item')
        
        if not file:
            return create_response(404, {"message": "File not found"})
            
        # Check if the file belongs to the user
        if file.get('userId') != user['id']:
            return create_response(403, {"message": "Access denied"})
        
        # Delete all transactions for the file
        try:
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
            logger.error(f"Error deleting transactions for file {file_id}: {str(e)}")
            return create_response(500, {"message": "Error deleting transactions"})
            
    except Exception as e:
        logger.error(f"Error in delete_file_transactions_handler: {str(e)}")
        return create_response(500, {"message": "Internal server error"})

def get_file_content_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Get the content of a file by ID."""
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
        
        # Get the file content from S3
        try:
            s3_response = s3_client.get_object(
                Bucket=FILE_STORAGE_BUCKET,
                Key=file.get('s3Key')
            )
            content = s3_response['Body'].read().decode('utf-8')
            
            return create_response(200, {
                'fileId': file_id,
                'content': content,
                'contentType': file.get('contentType'),
                'fileName': file.get('fileName')
            })
        except Exception as s3_error:
            logger.error(f"Error reading file from S3: {str(s3_error)}")
            return create_response(500, {"message": "Error reading file content"})
            
    except Exception as e:
        logger.error(f"Error getting file content: {str(e)}")
        return create_response(500, {"message": "Error getting file content"})

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
    else:
        return create_response(400, {"message": f"Unsupported route: {route}"}) 