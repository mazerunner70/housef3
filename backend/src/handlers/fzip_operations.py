"""
FZIP Operations Handler

Provides unified API endpoints for FZIP (Financial ZIP) backup/restore functionality:
- POST /fzip/backup - Initiate new FZIP backup
- GET /fzip/backup/{jobId}/status - Check FZIP backup status  
- GET /fzip/backup/{jobId}/download - Download FZIP package
- DELETE /fzip/backup/{jobId} - Delete FZIP backup
- GET /fzip/backup - List user's FZIP backups
- POST /fzip/restore - Create new FZIP restore job
- GET /fzip/restore - List user's FZIP restores
- GET /fzip/restore/{jobId}/status - Get FZIP restore status
- DELETE /fzip/restore/{jobId} - Delete FZIP restore job
- POST /fzip/restore/{jobId}/upload - Upload FZIP package and start restore
"""

import json
import logging
import os
import traceback
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

from models.fzip import (
    FZIPJob, FZIPBackupRequest, FZIPRestoreRequest, FZIPResponse, FZIPStatusResponse,
    FZIPStatus, FZIPType, FZIPBackupType, FZIPFormat,
    create_backup_job as create_fzip_backup_job, create_restore_job as create_fzip_restore_job
)
from services.fzip_service import fzip_service
from services.event_service import event_service
from models.events import BackupCompletedEvent, BackupFailedEvent
from utils.auth import get_user_from_event
from utils.fzip_metrics import fzip_metrics
from utils.lambda_utils import (
    create_response, mandatory_path_parameter, optional_body_parameter,
    mandatory_body_parameter, handle_error
)
from utils.db_utils import (
    create_fzip_job, get_fzip_job, update_fzip_job, 
    list_user_fzip_jobs, delete_fzip_job
)
from utils.s3_dao import get_presigned_post_url, put_object

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Use unified FZIP service
fzip_service_instance = fzip_service

# Constants
INTERNAL_SERVER_ERROR_MESSAGE = "Internal server error"
INVALID_JOB_ID_FORMAT_MESSAGE = "Invalid job ID format"
INVALID_BACKUP_JOB_NOT_FOUND_MESSAGE = "FZIP backup job not found"
INVALID_RESTORE_JOB_NOT_FOUND_MESSAGE = "FZIP restore job not found"

class FZIPEncoder(json.JSONEncoder):
    """Custom JSON encoder for FZIP operations"""
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, 'model_dump'):  # Pydantic models
            return obj.model_dump(by_alias=True)
        return super(FZIPEncoder, self).default(obj)


# ============================================================================
# BACKUP OPERATIONS
# ============================================================================

def initiate_fzip_backup_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Initiate a new FZIP backup job
    POST /fzip/backup
    """
    try:
        # Parse request body
        body_str = event.get('body')
        if not body_str:
            # Use default values for empty body
            request_data = {}
        else:
            try:
                request_data = json.loads(body_str)
            except json.JSONDecodeError:
                return create_response(400, {"error": "Invalid JSON format in request body"})
        
        # Validate and create backup request
        try:
            backup_request = FZIPBackupRequest.model_validate(request_data)
        except Exception as e:
            return create_response(400, {"error": "Invalid FZIP backup request", "details": str(e)})
        
        # Create FZIP backup job using the unified model
        fzip_job = create_fzip_backup_job(user_id, backup_request)
        
        # Store backup job in database
        create_fzip_job(fzip_job)
        
        # Process backup asynchronously (simplified for Phase 1)
        try:
            processed_job = process_fzip_backup_job(fzip_job)
            
            # Create response
            response = FZIPResponse(
                jobId=processed_job.job_id,
                jobType=processed_job.job_type,
                status=processed_job.status,
                packageFormat=FZIPFormat.FZIP,
                estimatedSize=f"~{processed_job.package_size or 0}B" if processed_job.package_size else None
            )
            
            return create_response(201, response.model_dump(by_alias=True))
            
        except Exception as e:
            logger.error(f"FZIP backup processing failed: {str(e)}")
            
            # Update job status to failed
            fzip_job.status = FZIPStatus.BACKUP_FAILED
            fzip_job.error = str(e)
            update_fzip_job(fzip_job)
            
            # Publish failure event
            failure_event = BackupFailedEvent(
                user_id=user_id,
                backup_id=str(fzip_job.job_id),
                error=str(e)
            )
            event_service.publish_event(failure_event)
            
            return create_response(500, {
                "error": "FZIP backup processing failed",
                "jobId": str(fzip_job.job_id),
                "message": str(e),
                "packageFormat": "fzip"
            })
        
    except Exception as e:
        logger.error(f"Error initiating FZIP backup: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"error": INTERNAL_SERVER_ERROR_MESSAGE, "message": str(e)})


def get_fzip_backup_status_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Get FZIP backup job status
    GET /fzip/backup/{jobId}/status
    """
    try:
        job_id = mandatory_path_parameter(event, 'jobId')
               
        # Retrieve backup job from database
        backup_job = get_fzip_job(job_id, user_id)
        if not backup_job:
            return create_response(404, {"error": INVALID_BACKUP_JOB_NOT_FOUND_MESSAGE})
        
        # Create response from actual job data
        response = FZIPStatusResponse(
            jobId=backup_job.job_id,
            jobType=backup_job.job_type,
            status=backup_job.status,
            progress=backup_job.progress,
            currentPhase=backup_job.current_phase,
            downloadUrl=backup_job.download_url,
            expiresAt=datetime.fromtimestamp(backup_job.expires_at / 1000, timezone.utc).isoformat() if backup_job.expires_at else None,
            packageSize=backup_job.package_size,
            completedAt=datetime.fromtimestamp(backup_job.completed_at / 1000, timezone.utc).isoformat() if backup_job.completed_at else None,
            error=backup_job.error,
            packageFormat=backup_job.package_format,
            createdAt=backup_job.created_at
        )
        
        return create_response(200, response.model_dump(by_alias=True))
        
    except Exception as e:
        logger.error(f"Error getting FZIP backup status: {str(e)}")
        return create_response(500, {"error": INTERNAL_SERVER_ERROR_MESSAGE, "message": str(e)})


def get_fzip_backup_download_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Get download URL for FZIP backup package
    GET /fzip/backup/{jobId}/download
    """
    try:
        job_id = mandatory_path_parameter(event, 'jobId')
               
        # Retrieve backup job from database and check ownership
        backup_job = get_fzip_job(job_id, user_id)
        if not backup_job:
            return create_response(404, {"error": INVALID_BACKUP_JOB_NOT_FOUND_MESSAGE})
        
        # Check if backup is completed
        if backup_job.status != FZIPStatus.BACKUP_COMPLETED:
            return create_response(400, {"error": "FZIP backup job is not completed yet"})
        
        # Check if backup has expired
        if backup_job.expires_at and datetime.now(timezone.utc).timestamp() * 1000 > backup_job.expires_at:
            return create_response(410, {"error": "FZIP backup package has expired"})
        
        # Generate presigned URL for the backup package
        if not backup_job.s3_key:
            return create_response(404, {"error": "FZIP backup package not found"})
        
        try:
            download_url = fzip_service_instance.generate_download_url(backup_job.s3_key)
            
            # Return redirect response  
            return {
                "statusCode": 302,
                "headers": {
                    "Location": download_url,
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({"downloadUrl": download_url, "packageFormat": "fzip"})
            }
            
        except Exception as e:
            logger.error(f"Failed to generate download URL: {str(e)}")
            return create_response(404, {"error": "FZIP backup package not found or expired"})
        
    except Exception as e:
        logger.error(f"Error getting FZIP backup download: {str(e)}")
        return create_response(500, {"error": INTERNAL_SERVER_ERROR_MESSAGE, "message": str(e)})


def list_fzip_backups_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    List user's FZIP backup jobs
    GET /fzip/backup
    """
    try:
        # Parse pagination parameters
        limit = int(event.get('queryStringParameters', {}).get('limit', 20))
        offset = int(event.get('queryStringParameters', {}).get('offset', 0))
        
        # Limit the maximum page size
        limit = min(limit, 100)
        
        # Retrieve backup jobs from database
        backup_jobs, pagination_key = list_user_fzip_jobs(user_id, FZIPType.BACKUP.value, limit)
        
        # Convert to response format
        backups_data = []
        for job in backup_jobs:
            backups_data.append({
                "jobId": str(job.job_id),
                "jobType": job.job_type.value,
                "status": job.status.value,
                "backupType": job.backup_type.value if job.backup_type else None,
                "createdAt": job.created_at,
                "completedAt": job.completed_at,
                "progress": job.progress,
                "packageSize": job.package_size,
                "description": job.description,
                "packageFormat": "fzip"
            })
        
        return create_response(200, {
            "backups": backups_data,
            "total": len(backups_data),
            "limit": limit,
            "offset": offset,
            "hasMore": pagination_key is not None,
            "packageFormat": "fzip"
        })
        
    except Exception as e:
        logger.error(f"Error listing FZIP backups: {str(e)}")
        return create_response(500, {"error": INTERNAL_SERVER_ERROR_MESSAGE, "message": str(e)})


def delete_fzip_backup_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Delete an FZIP backup job and its package
    DELETE /fzip/backup/{jobId}
    """
    try:
        job_id = mandatory_path_parameter(event, 'jobId')

        # Retrieve backup job from database and check ownership
        backup_job = get_fzip_job(job_id, user_id)
        if not backup_job:
            return create_response(404, {"error": INVALID_BACKUP_JOB_NOT_FOUND_MESSAGE})
        
        # Delete backup package from S3 if it exists
        if backup_job.s3_key:
            try:
                from utils.s3_dao import delete_object
                delete_object(backup_job.s3_key)
                logger.info(f"Deleted FZIP backup package from S3: {backup_job.s3_key}")
            except Exception as e:
                logger.warning(f"Failed to delete FZIP backup package from S3: {str(e)}")
                # Continue with database deletion even if S3 deletion fails
        
        # Delete backup job from database
        success = delete_fzip_job(job_id, user_id)
        if not success:
            return create_response(500, {"error": "Failed to delete FZIP backup job"})   
        logger.info(f"FZIP backup {job_id} deleted for user {user_id}")
        
        return create_response(200, {"message": "FZIP backup deleted successfully"})
        
    except Exception as e:
        logger.error(f"Error deleting FZIP backup: {str(e)}")
        return create_response(500, {"error": INTERNAL_SERVER_ERROR_MESSAGE, "message": str(e)})


def process_fzip_backup_job(fzip_job: FZIPJob) -> FZIPJob:
    """
    Process an FZIP backup job (simplified for Phase 1)
    In production, this would be handled by a separate Lambda or async process
    """
    backup_type = fzip_job.backup_type.value if fzip_job.backup_type else "complete"
    
    fzip_metrics.measure_backup_duration(backup_type, fzip_job.user_id)
    try:
        logger.info(f"Processing FZIP backup job: {fzip_job.job_id}")
        
        # Update status to processing
        fzip_job.status = FZIPStatus.BACKUP_PROCESSING
        fzip_job.progress = 10
        fzip_job.current_phase = "collecting_data"
        update_fzip_job(fzip_job)

        # Collect user data
        backup_type_enum = fzip_job.backup_type or FZIPBackupType.COMPLETE
        collected_data = fzip_service_instance.collect_backup_data(
            user_id=fzip_job.user_id,
            backup_type=backup_type_enum,
            include_analytics=fzip_job.include_analytics,
            **(fzip_job.parameters or {})
        )
        
        fzip_job.progress = 60
        fzip_job.current_phase = "building_fzip_package"
        update_fzip_job(fzip_job)        
        
        # Build FZIP backup package
        s3_key, package_size = fzip_service_instance.build_backup_package(fzip_job, collected_data)
        
        fzip_job.progress = 90
        fzip_job.current_phase = "generating_download_url"
        update_fzip_job(fzip_job)
        
        # Generate download URL
        download_url = fzip_service_instance.generate_download_url(s3_key)
        
        # Update job with results
        fzip_job.status = FZIPStatus.BACKUP_COMPLETED
        fzip_job.progress = 100
        fzip_job.current_phase = "completed"
        fzip_job.s3_key = s3_key
        fzip_job.package_size = package_size
        fzip_job.download_url = download_url
        fzip_job.completed_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        update_fzip_job(fzip_job)
        
        # Publish completion event
        completion_event = BackupCompletedEvent(
            user_id=fzip_job.user_id,
            backup_id=str(fzip_job.job_id),
            package_size=package_size,
            s3_key=s3_key,
            data_summary={
                "accounts": len(collected_data.get('accounts', [])),
                "transactions": len(collected_data.get('transactions', [])),
                "categories": len(collected_data.get('categories', [])),
                "file_maps": len(collected_data.get('file_maps', [])),
                "transaction_files": len(collected_data.get('transaction_files', []))
            }
        )
        event_service.publish_event(completion_event)
        
        logger.info(f"FZIP backup job completed: {fzip_job.job_id}")
        return fzip_job
        
    except Exception as e:
        logger.error(f"Failed to process FZIP backup job {fzip_job.job_id}: {str(e)}")
        fzip_job.status = FZIPStatus.BACKUP_FAILED
        fzip_job.error = str(e)
        update_fzip_job(fzip_job)
        
        # Record failure metrics
        fzip_metrics.record_backup_error(
            error_type=type(e).__name__,
            error_message=str(e),
            backup_type=backup_type,
            phase="overall_processing"
        )
        raise


# ============================================================================
# RESTORE OPERATIONS
# ============================================================================

def create_fzip_restore_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle POST /fzip/restore - Create a new FZIP restore job."""
    try:
        body = json.loads(event.get('body', '{}'))
        request = FZIPRestoreRequest(**body)
        
        # Create FZIP restore job using the unified model
        fzip_job = create_fzip_restore_job(user_id, request)
        
        create_fzip_job(fzip_job)
        
        # Generate upload URL for FZIP package
        upload_url_data = get_presigned_post_url(
            bucket="housef3-dev-restore-packages",
            key=f"packages/{fzip_job.job_id}.fzip",  # Use .fzip extension
            expires_in=3600,
            conditions=[
                {'content-length-range': [1, 1024 * 1024 * 100]}  # 1 byte to 100MB
            ]
        )
        
        response = FZIPResponse(
            jobId=fzip_job.job_id,
            jobType=fzip_job.job_type,
            status=fzip_job.status,
            packageFormat=FZIPFormat.FZIP,
            message="FZIP restore job created successfully",
            uploadUrl=upload_url_data
        )
        
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': json.dumps(response.model_dump(by_alias=True))
        }
        
    except Exception as e:
        logger.error(f"Error creating FZIP restore job: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Failed to create FZIP restore job: {str(e)}'})
        }


def list_fzip_restores_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle GET /fzip/restore - List user's FZIP restore jobs."""
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        limit = int(query_params.get('limit', 20))
        last_evaluated_key = query_params.get('lastEvaluatedKey')
        
        # Get restore jobs
        restore_jobs, next_key = list_user_fzip_jobs(user_id, FZIPType.RESTORE.value, limit, last_evaluated_key)
        
        # Convert to response format
        jobs_data = []
        for job in restore_jobs:
            jobs_data.append({
                'jobId': str(job.job_id),
                'jobType': job.job_type.value,
                'status': job.status.value,
                'createdAt': job.created_at,
                'progress': job.progress,
                'currentPhase': job.current_phase,
                'packageSize': job.package_size,
                'packageFormat': 'fzip'
            })
        
        response_data = {
            'restoreJobs': jobs_data,
            'nextEvaluatedKey': next_key,
            'packageFormat': 'fzip'
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
        logger.error(f"Error listing FZIP restore jobs: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to list FZIP restore jobs: {str(e)}'})
        }


def get_fzip_restore_status_handler(event: Dict[str, Any], user_id: str, job_id: str) -> Dict[str, Any]:
    """Handle GET /fzip/restore/{jobId}/status - Get FZIP restore job status."""
    try:
        if not job_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': INVALID_JOB_ID_FORMAT_MESSAGE})
            }
        
        # Get restore job
        restore_job = get_fzip_job(job_id, user_id)
        if not restore_job:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': INVALID_RESTORE_JOB_NOT_FOUND_MESSAGE})
            }
        
        # Convert to response format
        response = FZIPStatusResponse(
            jobId=restore_job.job_id,
            jobType=restore_job.job_type,
            status=restore_job.status,
            progress=restore_job.progress,
            currentPhase=restore_job.current_phase,
            validationResults=restore_job.validation_results,
            restoreResults=restore_job.restore_results,
            error=restore_job.error,
            createdAt=restore_job.created_at,
            completedAt=datetime.fromtimestamp(restore_job.completed_at / 1000, timezone.utc).isoformat() if restore_job.completed_at else None,
            packageFormat=restore_job.package_format
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': json.dumps(response.model_dump(by_alias=True))
        }
        
    except Exception as e:
        logger.error(f"Error getting FZIP restore status: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to get FZIP restore status: {str(e)}'})
        }


def delete_fzip_restore_handler(event: Dict[str, Any], user_id: str, job_id: str) -> Dict[str, Any]:
    """Handle DELETE /fzip/restore/{jobId} - Delete FZIP restore job."""
    try:
        if not job_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': INVALID_JOB_ID_FORMAT_MESSAGE})
            }
        
        # Delete restore job
        success = delete_fzip_job(job_id, user_id)
        if not success:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'FZIP restore job not found or access denied'})
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
        logger.error(f"Error deleting FZIP restore job: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to delete FZIP restore job: {str(e)}'})
        }


def upload_fzip_package_handler(event: Dict[str, Any], user_id: str, job_id: str) -> Dict[str, Any]:
    """Handle POST /fzip/restore/{jobId}/upload - Upload FZIP package and start restore."""
    try:
        if not job_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': INVALID_JOB_ID_FORMAT_MESSAGE})
            }
        
        # Get restore job
        restore_job = get_fzip_job(job_id, user_id)
        if not restore_job:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': INVALID_RESTORE_JOB_NOT_FOUND_MESSAGE})
            }
        
        if restore_job.status != FZIPStatus.RESTORE_UPLOADED:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'FZIP restore job is not in uploaded state'})
            }
        
        # Parse multipart form data (simplified for this implementation)
        # In a real implementation, you'd need to parse the multipart form data
        # For now, we'll assume the package is uploaded via S3 directly
        
        # Update restore job status and start processing
        restore_job.status = FZIPStatus.RESTORE_VALIDATING
        restore_job.s3_key = f"packages/{job_id}.fzip"  # Use .fzip extension
        
        # Start restore processing
        fzip_service_instance.start_restore(restore_job, restore_job.s3_key)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': json.dumps({
                'message': 'FZIP restore processing started',
                'jobId': str(restore_job.job_id),
                'status': restore_job.status.value,
                'packageFormat': 'fzip'
            })
        }
        
    except Exception as e:
        logger.error(f"Error uploading FZIP package: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to upload FZIP package: {str(e)}'})
        }


# ============================================================================
# MAIN HANDLER
# ============================================================================

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for unified FZIP operations
    """
    try:
        # Get user from Cognito
        user = get_user_from_event(event)
        if not user:
            return create_response(401, {"message": "Unauthorized"})
        user_id = user.get('id')
        if not user_id:
            return create_response(401, {"message": "Unauthorized"})
        
        # Get route from event
        route = event.get('routeKey')
        if not route:
            return create_response(400, {"message": "Route not specified"})
        
        logger.info(f"Processing FZIP request: {route} for user {user_id}")
        
        # Route to appropriate handler
        if route == "POST /fzip/backup":
            return initiate_fzip_backup_handler(event, user_id)
        elif route == "GET /fzip/backup":
            return list_fzip_backups_handler(event, user_id)
        elif route == "GET /fzip/backup/{jobId}/status":
            return get_fzip_backup_status_handler(event, user_id)
        elif route == "GET /fzip/backup/{jobId}/download":
            return get_fzip_backup_download_handler(event, user_id)
        elif route == "DELETE /fzip/backup/{jobId}":
            return delete_fzip_backup_handler(event, user_id)
        elif route == "POST /fzip/restore":
            return create_fzip_restore_handler(event, user_id)
        elif route == "GET /fzip/restore":
            return list_fzip_restores_handler(event, user_id)
        elif route == "GET /fzip/restore/{jobId}/status":
            job_id = event.get('pathParameters', {}).get('jobId')
            return get_fzip_restore_status_handler(event, user_id, job_id)
        elif route == "DELETE /fzip/restore/{jobId}":
            job_id = event.get('pathParameters', {}).get('jobId')
            return delete_fzip_restore_handler(event, user_id, job_id)
        elif route == "POST /fzip/restore/{jobId}/upload":
            job_id = event.get('pathParameters', {}).get('jobId')
            return upload_fzip_package_handler(event, user_id, job_id)
        else:
            return create_response(400, {"message": f"Unsupported FZIP route: {route}"})
            
    except Exception as e:
        logger.error(f"FZIP operations handler error: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {
            "error": INTERNAL_SERVER_ERROR_MESSAGE,
            "message": "FZIP operations handler failed"
        })
