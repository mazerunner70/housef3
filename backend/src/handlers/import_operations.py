import json
import logging
import uuid
from typing import Dict, Any
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

from models.import_job import ImportJob, ImportStatus, ImportRequest, ImportResponse, ImportStatusResponse
from services.import_service import ImportService
from utils.db_utils import create_import_job, get_import_job, list_user_import_jobs, delete_import_job
from utils.auth import get_user_from_event
from utils.s3_dao import get_presigned_post_url, put_object

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize services
import_service = ImportService()

def lambda_handler(event, context):
    """Lambda handler for import operations."""
    try:
        # Extract HTTP method and path
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        path_parameters = event.get('pathParameters', {})
        
        # Get user from event
        user_info = get_user_from_event(event)
        if not user_info:
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'User not authenticated'})
            }
        
        user_id = user_info['id']
        
        # Route to appropriate handler
        if http_method == 'POST' and path == '/import':
            return handle_create_import(event, user_id)
        elif http_method == 'GET' and path == '/import':
            return handle_list_imports(event, user_id)
        elif http_method == 'GET' and path.startswith('/import/') and path.endswith('/status'):
            import_id = path_parameters.get('importId')
            return handle_get_import_status(event, user_id, import_id)
        elif http_method == 'DELETE' and path.startswith('/import/'):
            import_id = path_parameters.get('importId')
            return handle_delete_import(event, user_id, import_id)
        elif http_method == 'POST' and path.startswith('/import/') and path.endswith('/upload'):
            import_id = path_parameters.get('importId')
            return handle_upload_package(event, user_id, import_id)
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Endpoint not found'})
            }
            
    except Exception as e:
        logger.error(f"Error in import operations handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }

def handle_create_import(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle POST /import - Create a new import job."""
    try:
        body = json.loads(event.get('body', '{}'))
        request = ImportRequest(**body)
        
        # Create import job
        import_job = ImportJob(
            userId=user_id,
            status=ImportStatus.UPLOADED,
            mergeStrategy=request.merge_strategy,
            uploadedAt=int(datetime.now(timezone.utc).timestamp() * 1000),
            expiresAt=int((datetime.now(timezone.utc).timestamp() + 24 * 3600) * 1000)  # 24 hours
        )
        
        create_import_job(import_job)
        
        # Generate upload URL
        upload_url_data = get_presigned_post_url(
            bucket="housef3-dev-import-packages",
            key=f"packages/{import_job.import_id}.zip",
            expires_in=3600,
            conditions=[
                {'content-length-range': [1, 1024 * 1024 * 100]}  # 1 byte to 100MB
            ]
        )
        
        response = ImportResponse(
            importId=import_job.import_id,
            status=import_job.status,
            message="Import job created successfully"
        )
        
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': json.dumps({
                **response.dict(by_alias=True),
                'uploadUrl': upload_url_data
            })
        }
        
    except Exception as e:
        logger.error(f"Error creating import job: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Failed to create import job: {str(e)}'})
        }

def handle_list_imports(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle GET /import - List user's import jobs."""
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        limit = int(query_params.get('limit', 20))
        last_evaluated_key = query_params.get('lastEvaluatedKey')
        
        # Get import jobs
        import_jobs, next_key = list_user_import_jobs(user_id, limit, last_evaluated_key)
        
        # Convert to response format
        jobs_data = []
        for job in import_jobs:
            jobs_data.append({
                'importId': str(job.import_id),
                'status': job.status.value,
                'uploadedAt': job.uploaded_at,
                'progress': job.progress,
                'currentPhase': job.current_phase,
                'packageSize': job.package_size
            })
        
        response_data = {
            'importJobs': jobs_data,
            'nextEvaluatedKey': next_key
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        logger.error(f"Error listing import jobs: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to list import jobs: {str(e)}'})
        }

def handle_get_import_status(event: Dict[str, Any], user_id: str, import_id: str) -> Dict[str, Any]:
    """Handle GET /import/{importId}/status - Get import job status."""
    try:
        if not import_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Import ID is required'})
            }
        
        # Get import job
        import_job = get_import_job(import_id, user_id)
        if not import_job:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Import job not found'})
            }
        
        # Convert to response format
        response = ImportStatusResponse(
            importId=import_job.import_id,
            status=import_job.status,
            progress=import_job.progress,
            currentPhase=import_job.current_phase,
            validationResults=import_job.validation_results,
            importResults=import_job.import_results,
            errorMessage=import_job.error_message,
            uploadedAt=import_job.uploaded_at,
            completedAt=import_job.completed_at
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': json.dumps(response.dict(by_alias=True))
        }
        
    except Exception as e:
        logger.error(f"Error getting import status: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to get import status: {str(e)}'})
        }

def handle_delete_import(event: Dict[str, Any], user_id: str, import_id: str) -> Dict[str, Any]:
    """Handle DELETE /import/{importId} - Delete import job."""
    try:
        if not import_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Import ID is required'})
            }
        
        # Delete import job
        success = delete_import_job(import_id, user_id)
        if not success:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Import job not found or access denied'})
            }
        
        return {
            'statusCode': 204,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': ''
        }
        
    except Exception as e:
        logger.error(f"Error deleting import job: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to delete import job: {str(e)}'})
        }

def handle_upload_package(event: Dict[str, Any], user_id: str, import_id: str) -> Dict[str, Any]:
    """Handle POST /import/{importId}/upload - Upload package and start import."""
    try:
        if not import_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Import ID is required'})
            }
        
        # Get import job
        import_job = get_import_job(import_id, user_id)
        if not import_job:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Import job not found'})
            }
        
        if import_job.status != ImportStatus.UPLOADED:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Import job is not in uploaded state'})
            }
        
        # Parse multipart form data (simplified for this implementation)
        # In a real implementation, you'd need to parse the multipart form data
        # For now, we'll assume the package is uploaded via S3 directly
        
        # Update import job status and start processing
        import_job.status = ImportStatus.VALIDATING
        import_job.package_s3_key = f"packages/{import_id}.zip"
        
        # Start import processing
        import_service.start_import(import_job, import_job.package_s3_key)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': json.dumps({
                'message': 'Import processing started',
                'importId': str(import_job.import_id),
                'status': import_job.status.value
            })
        }
        
    except Exception as e:
        logger.error(f"Error uploading package: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to upload package: {str(e)}'})
        } 