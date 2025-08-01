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

Legacy endpoints (deprecated - use backup/restore instead):
- POST /fzip/export → POST /fzip/backup
- POST /fzip/import → POST /fzip/restore
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
    create_backup_job as create_fzip_backup_job, create_restore_job as create_fzip_restore_job,
    # Backward compatibility imports
    FZIPExportRequest, FZIPImportRequest, FZIPExportType,
    create_export_job as create_fzip_export_job, create_import_job as create_fzip_import_job
)
from services.fzip_service import fzip_service
from services.event_service import event_service
from models.events import ExportCompletedEvent, ExportFailedEvent
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
INVALID_EXPORT_JOB_NOT_FOUND_MESSAGE = "FZIP export job not found"
INVALID_IMPORT_JOB_NOT_FOUND_MESSAGE = "FZIP import job not found"

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
# EXPORT OPERATIONS
# ============================================================================

def initiate_fzip_export_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Initiate a new FZIP export job
    POST /fzip/export
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
        
        # Validate and create export request
        try:
            export_request = FZIPExportRequest.model_validate(request_data)
        except Exception as e:
            return create_response(400, {"error": "Invalid FZIP export request", "details": str(e)})
        
        # Create FZIP export job using the unified model
        fzip_job = create_fzip_export_job(user_id, export_request)
        
        # Store export job in database
        create_fzip_job(fzip_job)
        
        # Process export asynchronously (simplified for Phase 1)
        try:
            processed_job = process_fzip_export_job(fzip_job)
            
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
            logger.error(f"FZIP export processing failed: {str(e)}")
            
            # Update job status to failed
            fzip_job.status = FZIPStatus.BACKUP_FAILED
            fzip_job.error = str(e)
            update_fzip_job(fzip_job)
            
            # Publish failure event
            failure_event = ExportFailedEvent(
                user_id=user_id,
                export_id=str(fzip_job.job_id),
                export_type=fzip_job.backup_type.value if fzip_job.backup_type else "complete",
                error=str(e)
            )
            event_service.publish_event(failure_event)
            
            return create_response(500, {
                "error": "FZIP export processing failed",
                "jobId": str(fzip_job.job_id),
                "message": str(e),
                "packageFormat": "fzip"
            })
        
    except Exception as e:
        logger.error(f"Error initiating FZIP export: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"error": INTERNAL_SERVER_ERROR_MESSAGE, "message": str(e)})


def get_fzip_export_status_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Get FZIP export job status
    GET /fzip/export/{jobId}/status
    """
    try:
        job_id = mandatory_path_parameter(event, 'jobId')
               
        # Retrieve export job from database
        export_job = get_fzip_job(job_id, user_id)
        if not export_job:
            return create_response(404, {"error": INVALID_EXPORT_JOB_NOT_FOUND_MESSAGE})
        
        # Create response from actual job data
        response = FZIPStatusResponse(
            jobId=export_job.job_id,
            jobType=export_job.job_type,
            status=export_job.status,
            progress=export_job.progress,
            currentPhase=export_job.current_phase,
            downloadUrl=export_job.download_url,
            expiresAt=datetime.fromtimestamp(export_job.expires_at / 1000, timezone.utc).isoformat() if export_job.expires_at else None,
            packageSize=export_job.package_size,
            completedAt=datetime.fromtimestamp(export_job.completed_at / 1000, timezone.utc).isoformat() if export_job.completed_at else None,
            error=export_job.error,
            packageFormat=export_job.package_format,
            createdAt=export_job.created_at
        )
        
        return create_response(200, response.model_dump(by_alias=True))
        
    except Exception as e:
        logger.error(f"Error getting FZIP export status: {str(e)}")
        return create_response(500, {"error": INTERNAL_SERVER_ERROR_MESSAGE, "message": str(e)})


def get_fzip_export_download_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Get download URL for FZIP export package
    GET /fzip/export/{jobId}/download
    """
    try:
        job_id = mandatory_path_parameter(event, 'jobId')
               
        # Retrieve export job from database and check ownership
        export_job = get_fzip_job(job_id, user_id)
        if not export_job:
            return create_response(404, {"error": INVALID_EXPORT_JOB_NOT_FOUND_MESSAGE})
        
        # Check if export is completed
        if export_job.status != FZIPStatus.BACKUP_COMPLETED:
            return create_response(400, {"error": "FZIP export job is not completed yet"})
        
        # Check if export has expired
        if export_job.expires_at and datetime.now(timezone.utc).timestamp() * 1000 > export_job.expires_at:
            return create_response(410, {"error": "FZIP export package has expired"})
        
        # Generate presigned URL for the export package
        if not export_job.s3_key:
            return create_response(404, {"error": "FZIP export package not found"})
        
        try:
            download_url = fzip_service_instance.generate_download_url(export_job.s3_key)
            
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
            return create_response(404, {"error": "FZIP export package not found or expired"})
        
    except Exception as e:
        logger.error(f"Error getting FZIP export download: {str(e)}")
        return create_response(500, {"error": INTERNAL_SERVER_ERROR_MESSAGE, "message": str(e)})


def list_fzip_exports_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    List user's FZIP export jobs
    GET /fzip/export
    """
    try:
        # Parse pagination parameters
        limit = int(event.get('queryStringParameters', {}).get('limit', 20))
        offset = int(event.get('queryStringParameters', {}).get('offset', 0))
        
        # Limit the maximum page size
        limit = min(limit, 100)
        
        # Retrieve export jobs from database
        export_jobs, pagination_key = list_user_fzip_jobs(user_id, FZIPType.BACKUP.value, limit)
        
        # Convert to response format
        exports_data = []
        for job in export_jobs:
            exports_data.append({
                "jobId": str(job.job_id),
                "jobType": job.job_type.value,
                "status": job.status.value,
                "exportType": job.backup_type.value if job.backup_type else None,
                "createdAt": job.created_at,
                "completedAt": job.completed_at,
                "progress": job.progress,
                "packageSize": job.package_size,
                "description": job.description,
                "packageFormat": "fzip"
            })
        
        return create_response(200, {
            "exports": exports_data,
            "total": len(exports_data),
            "limit": limit,
            "offset": offset,
            "hasMore": pagination_key is not None,
            "packageFormat": "fzip"
        })
        
    except Exception as e:
        logger.error(f"Error listing FZIP exports: {str(e)}")
        return create_response(500, {"error": INTERNAL_SERVER_ERROR_MESSAGE, "message": str(e)})


def delete_fzip_export_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Delete an FZIP export job and its package
    DELETE /fzip/export/{jobId}
    """
    try:
        job_id = mandatory_path_parameter(event, 'jobId')

        # Retrieve export job from database and check ownership
        export_job = get_fzip_job(job_id, user_id)
        if not export_job:
            return create_response(404, {"error": INVALID_EXPORT_JOB_NOT_FOUND_MESSAGE})
        
        # Delete export package from S3 if it exists
        if export_job.s3_key:
            try:
                from utils.s3_dao import delete_object
                delete_object(export_job.s3_key)
                logger.info(f"Deleted FZIP export package from S3: {export_job.s3_key}")
            except Exception as e:
                logger.warning(f"Failed to delete FZIP export package from S3: {str(e)}")
                # Continue with database deletion even if S3 deletion fails
        
        # Delete export job from database
        success = delete_fzip_job(job_id, user_id)
        if not success:
            return create_response(500, {"error": "Failed to delete FZIP export job"})   
        logger.info(f"FZIP export {job_id} deleted for user {user_id}")
        
        return create_response(200, {"message": "FZIP export deleted successfully"})
        
    except Exception as e:
        logger.error(f"Error deleting FZIP export: {str(e)}")
        return create_response(500, {"error": INTERNAL_SERVER_ERROR_MESSAGE, "message": str(e)})


def process_fzip_export_job(fzip_job: FZIPJob) -> FZIPJob:
    """
    Process an FZIP export job (simplified for Phase 1)
    In production, this would be handled by a separate Lambda or async process
    """
    export_type = fzip_job.backup_type.value if fzip_job.backup_type else "complete"
    
    with fzip_metrics.measure_export_duration(export_type, fzip_job.user_id):
        try:
            logger.info(f"Processing FZIP export job: {fzip_job.job_id}")
            
            # Update status to processing
            fzip_job.status = FZIPStatus.BACKUP_PROCESSING
            fzip_job.progress = 10
            fzip_job.current_phase = "collecting_data"
            update_fzip_job(fzip_job)

            # Collect user data
            export_type_enum = fzip_job.backup_type or FZIPExportType.COMPLETE
            collected_data = fzip_service_instance.collect_user_data(
                user_id=fzip_job.user_id,
                export_type=export_type_enum,
                include_analytics=fzip_job.include_analytics,
                **(fzip_job.parameters or {})
            )
            
            fzip_job.progress = 60
            fzip_job.current_phase = "building_fzip_package"
            update_fzip_job(fzip_job)        
            
            # Build FZIP export package
            s3_key, package_size = fzip_service_instance.build_export_package(fzip_job, collected_data)
            
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
            completion_event = ExportCompletedEvent(
                user_id=fzip_job.user_id,
                export_id=str(fzip_job.job_id),
                export_type=fzip_job.backup_type.value if fzip_job.backup_type else "complete",
                package_size=package_size,
                download_url=download_url,
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
            
            logger.info(f"FZIP export job completed: {fzip_job.job_id}")
            return fzip_job
            
        except Exception as e:
            logger.error(f"Failed to process FZIP export job {fzip_job.job_id}: {str(e)}")
            fzip_job.status = FZIPStatus.BACKUP_FAILED
            fzip_job.error = str(e)
            update_fzip_job(fzip_job)
            
            # Record failure metrics
            fzip_metrics.record_export_error(
                error_type=type(e).__name__,
                error_message=str(e),
                export_type=export_type,
                phase="overall_processing"
            )
            raise


# ============================================================================
# IMPORT OPERATIONS
# ============================================================================

def create_fzip_import_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle POST /fzip/import - Create a new FZIP import job."""
    try:
        body = json.loads(event.get('body', '{}'))
        request = FZIPImportRequest(**body)
        
        # Create FZIP import job using the unified model
        fzip_job = create_fzip_import_job(user_id, request)
        
        create_fzip_job(fzip_job)
        
        # Generate upload URL for FZIP package
        upload_url_data = get_presigned_post_url(
            bucket="housef3-dev-import-packages",
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
            message="FZIP import job created successfully",
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
        logger.error(f"Error creating FZIP import job: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Failed to create FZIP import job: {str(e)}'})
        }


def list_fzip_imports_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle GET /fzip/import - List user's FZIP import jobs."""
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        limit = int(query_params.get('limit', 20))
        last_evaluated_key = query_params.get('lastEvaluatedKey')
        
        # Get import jobs
        import_jobs, next_key = list_user_fzip_jobs(user_id, FZIPType.RESTORE.value, limit, last_evaluated_key)
        
        # Convert to response format
        jobs_data = []
        for job in import_jobs:
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
            'importJobs': jobs_data,
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
        logger.error(f"Error listing FZIP import jobs: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to list FZIP import jobs: {str(e)}'})
        }


def get_fzip_import_status_handler(event: Dict[str, Any], user_id: str, job_id: str) -> Dict[str, Any]:
    """Handle GET /fzip/import/{jobId}/status - Get FZIP import job status."""
    try:
        if not job_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': INVALID_JOB_ID_FORMAT_MESSAGE})
            }
        
        # Get import job
        import_job = get_fzip_job(job_id, user_id)
        if not import_job:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': INVALID_IMPORT_JOB_NOT_FOUND_MESSAGE})
            }
        
        # Convert to response format
        response = FZIPStatusResponse(
            jobId=import_job.job_id,
            jobType=import_job.job_type,
            status=import_job.status,
            progress=import_job.progress,
            currentPhase=import_job.current_phase,
            validationResults=import_job.validation_results,
            restoreResults=import_job.restore_results,
            error=import_job.error,
            createdAt=import_job.created_at,
            completedAt=datetime.fromtimestamp(import_job.completed_at / 1000, timezone.utc).isoformat() if import_job.completed_at else None,
            packageFormat=import_job.package_format
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
        logger.error(f"Error getting FZIP import status: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to get FZIP import status: {str(e)}'})
        }


def delete_fzip_import_handler(event: Dict[str, Any], user_id: str, job_id: str) -> Dict[str, Any]:
    """Handle DELETE /fzip/import/{jobId} - Delete FZIP import job."""
    try:
        if not job_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': INVALID_JOB_ID_FORMAT_MESSAGE})
            }
        
        # Delete import job
        success = delete_fzip_job(job_id, user_id)
        if not success:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'FZIP import job not found or access denied'})
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
        logger.error(f"Error deleting FZIP import job: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to delete FZIP import job: {str(e)}'})
        }


def upload_fzip_package_handler(event: Dict[str, Any], user_id: str, job_id: str) -> Dict[str, Any]:
    """Handle POST /fzip/import/{jobId}/upload - Upload FZIP package and start import."""
    try:
        if not job_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': INVALID_JOB_ID_FORMAT_MESSAGE})
            }
        
        # Get import job
        import_job = get_fzip_job(job_id, user_id)
        if not import_job:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': INVALID_IMPORT_JOB_NOT_FOUND_MESSAGE})
            }
        
        if import_job.status != FZIPStatus.RESTORE_UPLOADED:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'FZIP import job is not in uploaded state'})
            }
        
        # Parse multipart form data (simplified for this implementation)
        # In a real implementation, you'd need to parse the multipart form data
        # For now, we'll assume the package is uploaded via S3 directly
        
        # Update import job status and start processing
        import_job.status = FZIPStatus.RESTORE_VALIDATING
        import_job.s3_key = f"packages/{job_id}.fzip"  # Use .fzip extension
        
        # Start import processing
        fzip_service_instance.start_restore(import_job, import_job.s3_key)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': json.dumps({
                'message': 'FZIP import processing started',
                'jobId': str(import_job.job_id),
                'status': import_job.status.value,
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
        # New backup/restore routes
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
        
        # Legacy export/import routes (backward compatibility)
        elif route == "POST /fzip/export":
            logger.warning(f"User {user_id} using deprecated /fzip/export endpoint. Use /fzip/backup instead.")
            return initiate_fzip_backup_handler(event, user_id)
        elif route == "GET /fzip/export":
            logger.warning(f"User {user_id} using deprecated /fzip/export endpoint. Use /fzip/backup instead.")
            return list_fzip_backups_handler(event, user_id)
        elif route == "GET /fzip/export/{jobId}/status":
            logger.warning(f"User {user_id} using deprecated /fzip/export endpoint. Use /fzip/backup instead.")
            return get_fzip_backup_status_handler(event, user_id)
        elif route == "GET /fzip/export/{jobId}/download":
            logger.warning(f"User {user_id} using deprecated /fzip/export endpoint. Use /fzip/backup instead.")
            return get_fzip_backup_download_handler(event, user_id)
        elif route == "DELETE /fzip/export/{jobId}":
            logger.warning(f"User {user_id} using deprecated /fzip/export endpoint. Use /fzip/backup instead.")
            return delete_fzip_backup_handler(event, user_id)
        elif route == "POST /fzip/import":
            logger.warning(f"User {user_id} using deprecated /fzip/import endpoint. Use /fzip/restore instead.")
            return create_fzip_restore_handler(event, user_id)
        elif route == "GET /fzip/import":
            logger.warning(f"User {user_id} using deprecated /fzip/import endpoint. Use /fzip/restore instead.")
            return list_fzip_restores_handler(event, user_id)
        elif route == "GET /fzip/import/{jobId}/status":
            logger.warning(f"User {user_id} using deprecated /fzip/import endpoint. Use /fzip/restore instead.")
            job_id = event.get('pathParameters', {}).get('jobId')
            return get_fzip_restore_status_handler(event, user_id, job_id)
        elif route == "DELETE /fzip/import/{jobId}":
            logger.warning(f"User {user_id} using deprecated /fzip/import endpoint. Use /fzip/restore instead.")
            job_id = event.get('pathParameters', {}).get('jobId')
            return delete_fzip_restore_handler(event, user_id, job_id)
        elif route == "POST /fzip/import/{jobId}/upload":
            logger.warning(f"User {user_id} using deprecated /fzip/import endpoint. Use /fzip/restore instead.")
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


# =============================================================================
# FUNCTION ALIASES FOR BACKUP/RESTORE TERMINOLOGY
# =============================================================================

# Backup handlers (aliases for export handlers)
initiate_fzip_backup_handler = initiate_fzip_export_handler
get_fzip_backup_status_handler = get_fzip_export_status_handler
get_fzip_backup_download_handler = get_fzip_export_download_handler
list_fzip_backups_handler = list_fzip_exports_handler
delete_fzip_backup_handler = delete_fzip_export_handler

# Restore handlers (aliases for import handlers)
create_fzip_restore_handler = create_fzip_import_handler
list_fzip_restores_handler = list_fzip_imports_handler
get_fzip_restore_status_handler = get_fzip_import_status_handler
delete_fzip_restore_handler = delete_fzip_import_handler

# Note: upload_fzip_package_handler is already generic and works for both backup and restore 