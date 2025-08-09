"""
S3 Consumer for FZIP Restore Packages

Triggered by S3 ObjectCreated events for keys under restore_packages/.
Parses metadata and key to determine userId and restoreId, creates/updates a FZIPJob,
runs initial validation only, and persists validation results and job status.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Dict, Optional

from models.fzip import FZIPJob, FZIPStatus, FZIPType, FZIPFormat
from services.fzip_service import fzip_service
from utils.db_utils import create_fzip_job, update_fzip_job, get_fzip_job
from utils.s3_dao import get_object_metadata


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _parse_user_and_restore_from_key(key: str) -> tuple[Optional[str], Optional[str]]:
    """Attempt to parse userId and restoreId from key: restore_packages/{userId}/{restoreId}.fzip"""
    try:
        parts = key.split('/')
        if len(parts) >= 3 and parts[0] == 'restore_packages':
            user_id = parts[1]
            restore_file = parts[2]
            if restore_file.endswith('.fzip'):
                restore_id = restore_file[:-5]
                return user_id, restore_id
        return None, None
    except Exception:
        return None, None


def _ensure_job(user_id: str, restore_id: str, s3_key: str, package_size: Optional[int]) -> FZIPJob:
    """Create or update the FZIPJob in validating state."""
    existing = get_fzip_job(restore_id, user_id)
    if existing:
        existing.status = FZIPStatus.RESTORE_VALIDATING
        existing.progress = 10
        existing.current_phase = "parsing_package"
        existing.s3_key = s3_key
        existing.package_size = package_size
        existing.package_format = FZIPFormat.FZIP
        existing.error = None
        update_fzip_job(existing)
        return existing

    job = FZIPJob(
        jobId=uuid.UUID(restore_id),
        userId=user_id,
        jobType=FZIPType.RESTORE,
        status=FZIPStatus.RESTORE_VALIDATING,
        packageFormat=FZIPFormat.FZIP,
        s3Key=s3_key,
        packageSize=package_size,
        progress=10,
        currentPhase="parsing_package",
    )
    create_fzip_job(job)
    return job


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda entrypoint for S3 event notifications.
    """
    try:
        records = event.get('Records', [])
        if not records:
            return _response(200, {"message": "No records"})

        for record in records:
            event_name = record.get('eventName', '')
            if not event_name.startswith('ObjectCreated'):
                logger.info(f"Skipping non-create event: {event_name}")
                continue

            bucket_name = record.get('s3', {}).get('bucket', {}).get('name')
            s3_key = record.get('s3', {}).get('object', {}).get('key')
            if not bucket_name or not s3_key:
                logger.warning("Missing bucket or key in record; skipping")
                continue

            # Read object metadata to get user and restore IDs
            meta = get_object_metadata(s3_key, bucket_name) or {}
            md = meta.get('metadata', {}) or {}
            user_id = md.get('userid') or md.get('userId')
            restore_id = md.get('restoreid') or md.get('restoreId')

            # Fallback: parse from key pattern
            if not user_id or not restore_id:
                parsed_user, parsed_restore = _parse_user_and_restore_from_key(s3_key)
                user_id = user_id or parsed_user
                restore_id = restore_id or parsed_restore

            if not user_id or not restore_id:
                logger.error(f"Could not determine userId/restoreId for key {s3_key}")
                continue

            # Ensure UUID format
            try:
                _ = uuid.UUID(restore_id)
            except Exception:
                logger.error(f"Invalid restoreId format (not UUID): {restore_id}")
                continue

            package_size = meta.get('content_length') if meta else None

            # Create or update job in validating state
            job = _ensure_job(user_id, restore_id, s3_key, package_size)

            # Perform initial validation only
            try:
                # Parse package
                package_data = fzip_service._parse_package(s3_key)

                # Schema validation
                job.current_phase = "validating_schema"
                job.progress = 20
                update_fzip_job(job)
                schema_results = fzip_service._validate_schema(package_data)
                job.validation_results['schema'] = schema_results
                if not schema_results.get('valid'):
                    job.status = FZIPStatus.RESTORE_VALIDATION_FAILED
                    job.error = "Schema validation failed"
                    update_fzip_job(job)
                    continue

                # Business rules validation
                job.current_phase = "validating_business_rules"
                job.progress = 30
                update_fzip_job(job)
                business_results = fzip_service._validate_business_rules(package_data, user_id)
                job.validation_results['business'] = business_results
                if not business_results.get('valid'):
                    job.status = FZIPStatus.RESTORE_VALIDATION_FAILED
                    job.error = "Business validation failed"
                    update_fzip_job(job)
                    continue

                # Empty profile validation
                empty_profile_results = fzip_service._validate_empty_profile(user_id)
                job.validation_results['profile'] = empty_profile_results
                if not empty_profile_results.get('valid'):
                    job.status = FZIPStatus.RESTORE_VALIDATION_FAILED
                    job.error = "Profile not empty"
                    update_fzip_job(job)
                    continue

                # Passed all validations
                job.status = FZIPStatus.RESTORE_VALIDATION_PASSED
                job.progress = 40
                job.current_phase = "validated_waiting_to_start"
                update_fzip_job(job)

            except Exception as e:
                logger.exception(f"Validation error for restore job {restore_id}: {e}")
                job.status = FZIPStatus.RESTORE_VALIDATION_FAILED
                job.error = str(e)
                update_fzip_job(job)
                continue

        return _response(200, {"message": "Processed records"})

    except Exception as e:
        logger.exception(f"Unhandled error in restore_consumer: {e}")
        return _response(500, {"error": "Internal error", "message": str(e)})


def _response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
        },
        'body': json.dumps(body),
    }


