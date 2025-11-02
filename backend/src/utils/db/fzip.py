"""
FZIP (File ZIP) job database operations.

This module provides CRUD operations for FZIP backup and restore jobs.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

from models.fzip import FZIPJob
from .base import (
    tables,
    dynamodb_operation,
    retry_on_throttle,
    monitor_performance,
)
from .helpers import batch_delete_items

logger = logging.getLogger(__name__)


# ============================================================================
# CRUD Operations
# ============================================================================

def create_fzip_job(fzip_job: FZIPJob) -> None:
    """
    Create a new FZIP job in DynamoDB.
    
    Args:
        fzip_job: The FZIPJob object to store
        
    Raises:
        ClientError: If there's a DynamoDB error
    """
    item = fzip_job.to_dynamodb_item()
    tables.fzip_jobs.put_item(Item=item)
    logger.info(f"Created FZIP job: {fzip_job.job_id} for user {fzip_job.user_id}")


@monitor_performance(warn_threshold_ms=200)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("get_fzip_job")
def get_fzip_job(job_id: str, user_id: str) -> Optional[FZIPJob]:
    """
    Retrieve a FZIP job by ID and user ID.
    
    Args:
        job_id: The FZIP job ID
        user_id: The user ID (for access control)
        
    Returns:
        FZIPJob object if found and owned by user, None otherwise
    """
    response = tables.fzip_jobs.get_item(Key={'jobId': job_id})
    
    if 'Item' in response:
        item = response['Item']
        # Check user ownership
        if item.get('userId') == user_id:
            return FZIPJob.from_dynamodb_item(item)
        else:
            logger.warning(f"User {user_id} attempted to access FZIP job {job_id} owned by {item.get('userId')}")
            return None
    return None


@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("update_fzip_job")
def update_fzip_job(fzip_job: FZIPJob) -> None:
    """
    Update an existing FZIP job in DynamoDB.
    
    Args:
        fzip_job: The FZIPJob object with updated details
        
    Raises:
        ClientError: If there's a DynamoDB error
    """
    item = fzip_job.to_dynamodb_item()
    tables.fzip_jobs.put_item(Item=item)
    logger.info(f"Updated FZIP job: {fzip_job.job_id}")


@monitor_performance(operation_type="query", warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("list_user_fzip_jobs")
def list_user_fzip_jobs(
    user_id: str,
    job_type: Optional[str] = None,
    limit: int = 20,
    last_evaluated_key: Optional[Dict[str, Any]] = None
) -> Tuple[List[FZIPJob], Optional[Dict[str, Any]]]:
    """
    List FZIP jobs for a user with pagination and optional job type filtering.
    
    Args:
        user_id: The user ID
        job_type: Optional job type filter ('backup' or 'restore')
        limit: Maximum number of jobs to return
        last_evaluated_key: For pagination
        
    Returns:
        Tuple of (fzip_jobs_list, next_pagination_key)
    """
    if job_type:
        # Use UserJobTypeIndex for filtering by job type
        query_params = {
            'IndexName': 'UserJobTypeIndex',
            'KeyConditionExpression': Key('userId').eq(user_id) & Key('jobType').eq(job_type),
            'Limit': limit,
            'ScanIndexForward': False  # Most recent first
        }
    else:
        # Use UserIdIndex for all jobs
        query_params = {
            'IndexName': 'UserIdIndex',
            'KeyConditionExpression': Key('userId').eq(user_id),
            'Limit': limit,
            'ScanIndexForward': False  # Most recent first
        }
    
    if last_evaluated_key:
        query_params['ExclusiveStartKey'] = last_evaluated_key
    
    response = tables.fzip_jobs.query(**query_params)
    
    fzip_jobs = []
    for item in response.get('Items', []):
        try:
            fzip_job = FZIPJob.from_dynamodb_item(item)
            fzip_jobs.append(fzip_job)
        except Exception as e:
            logger.error(f"Error creating FZIPJob from item: {str(e)}")
            continue
    
    pagination_key = response.get('LastEvaluatedKey')
    
    logger.info(f"Listed {len(fzip_jobs)} FZIP jobs for user {user_id}")
    return fzip_jobs, pagination_key


@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("delete_fzip_job")
def delete_fzip_job(job_id: str, user_id: str) -> bool:
    """
    Delete a FZIP job.
    
    Args:
        job_id: The FZIP job ID
        user_id: The user ID (for access control)
        
    Returns:
        True if deleted, False if not found or access denied
    """
    # First verify ownership
    fzip_job = get_fzip_job(job_id, user_id)
    if not fzip_job:
        logger.warning(f"FZIP job {job_id} not found or access denied for user {user_id}")
        return False
    
    # Delete the job
    tables.fzip_jobs.delete_item(Key={'jobId': job_id})
    logger.info(f"Deleted FZIP job: {job_id} for user {user_id}")
    return True


@monitor_performance(warn_threshold_ms=1000)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("cleanup_expired_fzip_jobs")
def cleanup_expired_fzip_jobs() -> int:
    """
    Clean up expired FZIP jobs.
    
    Returns:
        Number of jobs cleaned up
    """
    current_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    # Use ExpiresAtIndex for efficient querying
    response = tables.fzip_jobs.query(
        IndexName='ExpiresAtIndex',
        KeyConditionExpression=Key('expiresAt').lt(current_time)
    )
    
    expired_jobs = response.get('Items', [])
    
    if not expired_jobs:
        return 0
    
    # Delete expired jobs using batch helper
    cleanup_count = batch_delete_items(
        table=tables.fzip_jobs,
        items=expired_jobs,
        key_extractor=lambda job: {'jobId': job['jobId']}
    )
    
    logger.info(f"Cleaned up {cleanup_count} expired FZIP jobs")
    return cleanup_count

