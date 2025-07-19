"""
Export Operations Handler

Provides API endpoints for export functionality:
- POST /export - Initiate new export
- GET /export/{exportId}/status - Check export status  
- GET /export/{exportId}/download - Download export package
"""

import json
import logging
import os
import traceback
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from models.export import (
    ExportJob, ExportRequest, ExportResponse, ExportStatusResponse,
    ExportStatus, ExportType, ExportFormat
)
from services.export_service import ExportService
from services.event_service import event_service
from models.events import ExportCompletedEvent, ExportFailedEvent
from utils.auth import get_user_from_event
from utils.lambda_utils import (
    create_response, mandatory_path_parameter, optional_body_parameter,
    mandatory_body_parameter, handle_error
)
from utils.db_utils import (
    create_export_job, get_export_job, update_export_job, 
    list_user_export_jobs, delete_export_job
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize export service
export_service = ExportService()


class ExportEncoder(json.JSONEncoder):
    """Custom JSON encoder for export operations"""
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, 'model_dump'):  # Pydantic models
            return obj.model_dump(by_alias=True)
        return super(ExportEncoder, self).default(obj)


def initiate_export_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Initiate a new export job
    POST /export
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
            export_request = ExportRequest.model_validate(request_data)
        except Exception as e:
            return create_response(400, {"error": "Invalid export request", "details": str(e)})
        
        # Initiate export
        export_job = export_service.initiate_export(
            user_id=user_id,
            export_type=export_request.export_type,
            include_analytics=export_request.include_analytics,
            description=export_request.description,
            export_format=export_request.export_format,
            account_ids=export_request.account_ids,
            date_range_start=export_request.date_range_start,
            date_range_end=export_request.date_range_end,
            category_ids=export_request.category_ids
        )
        
        # Store export job in database
        create_export_job(export_job)
        
        # Process export asynchronously (simplified for Phase 1)
        try:
            processed_job = process_export_job(export_job)
            
            # Create response
            response = ExportResponse(
                exportId=processed_job.export_id,
                status=processed_job.status,
                estimatedSize=f"~{processed_job.package_size or 0}B" if processed_job.package_size else None,
                estimatedCompletion=None
            )
            
            return create_response(201, response.model_dump(by_alias=True))
            
        except Exception as e:
            logger.error(f"Export processing failed: {str(e)}")
            
            # Update job status to failed
            export_job.status = ExportStatus.FAILED
            export_job.error = str(e)
            update_export_job(export_job)
            
            # Publish failure event
            failure_event = ExportFailedEvent(
                user_id=user_id,
                export_id=str(export_job.export_id),
                export_type=export_job.export_type.value,
                error=str(e)
            )
            event_service.publish_event(failure_event)
            
            return create_response(500, {
                "error": "Export processing failed",
                "exportId": str(export_job.export_id),
                "message": str(e)
            })
        
    except Exception as e:
        logger.error(f"Error initiating export: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {"error": "Internal server error", "message": str(e)})


def get_export_status_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Get export job status
    GET /export/{exportId}/status
    """
    try:
        export_id = mandatory_path_parameter(event, 'exportId')
        
        try:
            export_uuid = uuid.UUID(export_id)
        except ValueError:
            return create_response(400, {"error": "Invalid export ID format"})
        
        # Retrieve export job from database
        export_job = get_export_job(export_id, user_id)
        if not export_job:
            return create_response(404, {"error": "Export job not found"})
        
        # Create response from actual job data
        response = ExportStatusResponse(
            exportId=export_job.export_id,
            status=export_job.status,
            progress=export_job.progress,
            currentPhase=export_job.current_phase,
            downloadUrl=export_job.download_url,
            expiresAt=datetime.fromtimestamp(export_job.expires_at / 1000, timezone.utc).isoformat() if export_job.expires_at else None,
            packageSize=export_job.package_size,
            completedAt=datetime.fromtimestamp(export_job.completed_at / 1000, timezone.utc).isoformat() if export_job.completed_at else None,
            error=export_job.error
        )
        
        return create_response(200, response.model_dump(by_alias=True))
        
    except Exception as e:
        logger.error(f"Error getting export status: {str(e)}")
        return create_response(500, {"error": "Internal server error", "message": str(e)})


def get_export_download_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Get download URL for export package
    GET /export/{exportId}/download
    """
    try:
        export_id = mandatory_path_parameter(event, 'exportId')
        
        try:
            export_uuid = uuid.UUID(export_id)
        except ValueError:
            return create_response(400, {"error": "Invalid export ID format"})
        
        # Retrieve export job from database and check ownership
        export_job = get_export_job(export_id, user_id)
        if not export_job:
            return create_response(404, {"error": "Export job not found"})
        
        # Check if export is completed
        if export_job.status != ExportStatus.COMPLETED:
            return create_response(400, {"error": "Export job is not completed yet"})
        
        # Check if export has expired
        if export_job.expires_at and datetime.now(timezone.utc).timestamp() * 1000 > export_job.expires_at:
            return create_response(410, {"error": "Export package has expired"})
        
        # Generate presigned URL for the export package
        if not export_job.s3_key:
            return create_response(404, {"error": "Export package not found"})
        
        try:
            download_url = export_service.generate_download_url(export_job.s3_key)
            
            # Return redirect response  
            return {
                "statusCode": 302,
                "headers": {
                    "Location": download_url,
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({"downloadUrl": download_url})
            }
            
        except Exception as e:
            logger.error(f"Failed to generate download URL: {str(e)}")
            return create_response(404, {"error": "Export package not found or expired"})
        
    except Exception as e:
        logger.error(f"Error getting export download: {str(e)}")
        return create_response(500, {"error": "Internal server error", "message": str(e)})


def list_exports_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    List user's export jobs
    GET /export
    """
    try:
        # Parse pagination parameters
        limit = int(event.get('queryStringParameters', {}).get('limit', 20))
        offset = int(event.get('queryStringParameters', {}).get('offset', 0))
        
        # Limit the maximum page size
        limit = min(limit, 100)
        
        # Retrieve export jobs from database
        export_jobs, pagination_key = list_user_export_jobs(user_id, limit=limit)
        
        # Convert to response format
        exports_data = []
        for job in export_jobs:
            exports_data.append({
                "exportId": str(job.export_id),
                "status": job.status.value,
                "exportType": job.export_type.value,
                "requestedAt": job.requested_at,
                "completedAt": job.completed_at,
                "progress": job.progress,
                "packageSize": job.package_size,
                "description": job.description
            })
        
        return create_response(200, {
            "exports": exports_data,
            "total": len(exports_data),
            "limit": limit,
            "offset": offset,
            "hasMore": pagination_key is not None
        })
        
    except Exception as e:
        logger.error(f"Error listing exports: {str(e)}")
        return create_response(500, {"error": "Internal server error", "message": str(e)})


def delete_export_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Delete an export job and its package
    DELETE /export/{exportId}
    """
    try:
        export_id = mandatory_path_parameter(event, 'exportId')
        
        try:
            export_uuid = uuid.UUID(export_id)
        except ValueError:
            return create_response(400, {"error": "Invalid export ID format"})
        
        # Retrieve export job from database and check ownership
        export_job = get_export_job(export_id, user_id)
        if not export_job:
            return create_response(404, {"error": "Export job not found"})
        
        # Delete export package from S3 if it exists
        if export_job.s3_key:
            try:
                from utils.s3_dao import delete_object
                delete_object(export_job.s3_key)
                logger.info(f"Deleted export package from S3: {export_job.s3_key}")
            except Exception as e:
                logger.warning(f"Failed to delete export package from S3: {str(e)}")
                # Continue with database deletion even if S3 deletion fails
        
        # Delete export job from database
        success = delete_export_job(export_id, user_id)
        if not success:
            return create_response(500, {"error": "Failed to delete export job"})
        
        logger.info(f"Export {export_id} deleted for user {user_id}")
        
        return create_response(200, {"message": "Export deleted successfully"})
        
    except Exception as e:
        logger.error(f"Error deleting export: {str(e)}")
        return create_response(500, {"error": "Internal server error", "message": str(e)})


def process_export_job(export_job: ExportJob) -> ExportJob:
    """
    Process an export job (simplified for Phase 1)
    In production, this would be handled by a separate Lambda or async process
    """
    try:
        logger.info(f"Processing export job: {export_job.export_id}")
        
        # Update status to processing
        export_job.status = ExportStatus.PROCESSING
        export_job.progress = 10
        export_job.current_phase = "collecting_data"
        update_export_job(export_job)
        
        # Collect user data
        collected_data = export_service.collect_user_data(
            user_id=export_job.user_id,
            export_type=export_job.export_type,
            include_analytics=export_job.include_analytics,
            **(export_job.parameters or {})
        )
        
        export_job.progress = 60
        export_job.current_phase = "building_package"
        update_export_job(export_job)
        
        # Build export package
        s3_key, package_size = export_service.build_export_package(export_job, collected_data)
        
        export_job.progress = 90
        export_job.current_phase = "generating_download_url"
        update_export_job(export_job)
        
        # Generate download URL
        download_url = export_service.generate_download_url(s3_key)
        
        # Update job with results
        export_job.status = ExportStatus.COMPLETED
        export_job.progress = 100
        export_job.current_phase = "completed"
        export_job.s3_key = s3_key
        export_job.package_size = package_size
        export_job.download_url = download_url
        export_job.completed_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        update_export_job(export_job)
        
        # Publish completion event
        completion_event = ExportCompletedEvent(
            user_id=export_job.user_id,
            export_id=str(export_job.export_id),
            export_type=export_job.export_type.value,
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
        
        logger.info(f"Export job completed: {export_job.export_id}")
        return export_job
        
    except Exception as e:
        logger.error(f"Failed to process export job {export_job.export_id}: {str(e)}")
        export_job.status = ExportStatus.FAILED
        export_job.error = str(e)
        update_export_job(export_job)
        raise


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for export operations
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
        
        logger.info(f"Processing export request: {route} for user {user_id}")
        
        # Route to appropriate handler
        if route == "POST /export":
            return initiate_export_handler(event, user_id)
        elif route == "GET /export":
            return list_exports_handler(event, user_id)
        elif route == "GET /export/{exportId}/status":
            return get_export_status_handler(event, user_id)
        elif route == "GET /export/{exportId}/download":
            return get_export_download_handler(event, user_id)
        elif route == "DELETE /export/{exportId}":
            return delete_export_handler(event, user_id)
        else:
            return create_response(400, {"message": f"Unsupported route: {route}"})
            
    except Exception as e:
        logger.error(f"Export operations handler error: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {
            "error": "Internal server error",
            "message": "Export operations handler failed"
        }) 