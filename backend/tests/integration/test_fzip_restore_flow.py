import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Tuple, Optional, List
from unittest.mock import patch

from models.fzip import FZIPJob, FZIPStatus, FZIPType
from src.consumers import restore_consumer as consumer
from src.handlers import fzip_operations as ops


class InMemoryJobStore:
    def __init__(self):
        self.store: Dict[Tuple[str, str], FZIPJob] = {}

    def create(self, job: FZIPJob):
        self.store[(str(job.job_id), job.user_id)] = job
        return True

    def update(self, job: FZIPJob):
        self.store[(str(job.job_id), job.user_id)] = job
        return True

    def get(self, job_id: str, user_id: str) -> Optional[FZIPJob]:
        return self.store.get((job_id, user_id))

    def list_for_user(self, user_id: str, job_type: Optional[str], limit: int, last_key=None):
        items: List[FZIPJob] = [j for (jid, uid), j in self.store.items() if uid == user_id]
        if job_type:
            items = [j for j in items if j.job_type.value == job_type]
        return items[:limit], None


def _s3_event(bucket: str, key: str):
    return {
        'Records': [
            {
                'eventName': 'ObjectCreated:Put',
                's3': {'bucket': {'name': bucket}, 'object': {'key': key}},
            }
        ]
    }


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


@patch('services.fzip_service.FZIPService._validate_empty_profile')
@patch('services.fzip_service.FZIPService._validate_business_rules')
@patch('services.fzip_service.FZIPService._validate_schema')
@patch('services.fzip_service.FZIPService._parse_package')
@patch('src.handlers.fzip_operations.list_user_fzip_jobs')
@patch('src.handlers.fzip_operations.get_fzip_job')
@patch('src.handlers.fzip_operations.update_fzip_job')
@patch('src.handlers.fzip_operations.create_fzip_job')
@patch('src.consumers.restore_consumer.get_object_metadata')
@patch('src.consumers.restore_consumer.list_user_fzip_jobs')
@patch('src.consumers.restore_consumer.get_fzip_job')
@patch('src.consumers.restore_consumer.update_fzip_job')
@patch('src.consumers.restore_consumer.create_fzip_job')
def test_upload_s3_event_validation_and_listing(
    mock_consumer_create,
    mock_consumer_update,
    mock_consumer_get,
    mock_consumer_list,
    mock_head,
    mock_handler_create,
    mock_handler_update,
    mock_handler_get,
    mock_handler_list,
    mock_parse,
    mock_schema,
    mock_business,
    mock_empty,
):
    user_id = 'itest-user'
    restore_id = str(uuid.uuid4())
    key = f'restore_packages/{user_id}/{restore_id}.fzip'

    # In-memory store used by both consumer and handler patches
    store = InMemoryJobStore()

    # Wire DB functions in both modules to the same store
    mock_consumer_create.side_effect = store.create
    mock_consumer_update.side_effect = store.update
    mock_consumer_get.side_effect = store.get
    mock_consumer_list.side_effect = store.list_for_user

    mock_handler_create.side_effect = store.create
    mock_handler_update.side_effect = store.update
    mock_handler_get.side_effect = store.get
    mock_handler_list.side_effect = store.list_for_user

    # S3 metadata and package parsing/validation pass
    mock_head.return_value = {'metadata': {'userid': user_id, 'restoreid': restore_id}, 'content_length': 1024}
    mock_parse.return_value = {'manifest': {'user_id': user_id}, 'data': {}, 'raw': b''}
    mock_schema.return_value = {'valid': True}
    mock_business.return_value = {'valid': True}
    mock_empty.return_value = {'valid': True}

    # Run consumer on S3 event
    resp = consumer.handler(_s3_event('bucket-x', key), None)
    assert resp['statusCode'] == 200

    # List via handler helper to verify job is visible with validation passed
    list_resp = ops.list_fzip_restores_handler({'queryStringParameters': {}}, user_id)
    assert list_resp['statusCode'] == 200
    body = json.loads(list_resp['body'])
    jobs = body['restoreJobs']
    assert len(jobs) == 1
    assert jobs[0]['status'] == 'restore_validation_passed'
    assert jobs[0]['progress'] == 40


@patch('services.fzip_service.create_transaction')
@patch('services.fzip_service.create_transaction_file')
@patch('services.fzip_service.create_file_map')
@patch('services.fzip_service.create_category_in_db')
@patch('services.fzip_service.create_account')
@patch('services.fzip_service.put_object')
@patch('services.fzip_service.FZIPService._parse_package')
@patch('src.handlers.fzip_operations.get_fzip_job')
@patch('src.handlers.fzip_operations.update_fzip_job')
def test_start_restore_completes(
    mock_update,
    mock_get,
    mock_parse,
    mock_put,
    mock_create_account,
    mock_create_category,
    mock_create_file_map,
    mock_create_tf,
    mock_create_txn,
):
    user_id = 'itest-user-2'
    restore_id = str(uuid.uuid4())
    key = f'restore_packages/{user_id}/{restore_id}.fzip'

    # Prepare job in a simple closure-backed store
    store = InMemoryJobStore()
    job = FZIPJob(jobId=uuid.UUID(restore_id), userId=user_id, jobType=FZIPType.RESTORE, status=FZIPStatus.RESTORE_VALIDATION_PASSED, s3Key=key)
    store.create(job)

    # get/update wired to the store used by handler
    mock_get.side_effect = store.get
    mock_update.side_effect = store.update

    # Minimal package with empty data but valid structure
    mock_parse.return_value = {'manifest': {'user_id': user_id}, 'data': {e: [] for e in ['accounts', 'categories', 'file_maps', 'transaction_files', 'transactions']}, 'raw': b''}

    # Invoke start handler
    resp = ops.start_fzip_restore_handler({'pathParameters': {'jobId': restore_id}}, user_id, restore_id)
    assert resp['statusCode'] == 200

    # Final job state should be completed
    final = store.get(restore_id, user_id)
    assert final is not None
    assert final.status == FZIPStatus.RESTORE_COMPLETED
    assert final.progress == 100
    assert final.current_phase == 'completed'


@patch('src.handlers.fzip_operations.get_fzip_job')
@patch('src.handlers.fzip_operations.update_fzip_job')
@patch('services.fzip_service.FZIPService._parse_package')
@patch('services.fzip_service.get_fzip_job')
def test_start_restore_cancel_midway(
    mock_service_get,
    mock_parse,
    mock_update,
    mock_handler_get,
):
    user_id = 'itest-user-3'
    restore_id = str(uuid.uuid4())
    key = f'restore_packages/{user_id}/{restore_id}.fzip'

    # Prepare job in store
    store = InMemoryJobStore()
    job = FZIPJob(jobId=uuid.UUID(restore_id), userId=user_id, jobType=FZIPType.RESTORE, status=FZIPStatus.RESTORE_VALIDATION_PASSED, s3Key=key)
    store.create(job)

    # Handler get/update wired to store
    mock_handler_get.side_effect = store.get
    mock_update.side_effect = store.update

    # Minimal parse result
    mock_parse.return_value = {'manifest': {'user_id': user_id}, 'data': {e: [] for e in ['accounts', 'categories', 'file_maps', 'transaction_files', 'transactions']}, 'raw': b''}

    # Service get_fzip_job will return a canceled status on first check to trigger cancel
    canceled_once = {'called': False}

    def service_get(job_id: str, u: str):
        if not canceled_once['called']:
            canceled_once['called'] = True
            # Return a canceled job to trigger CanceledException
            return FZIPJob(jobId=uuid.UUID(job_id), userId=u, jobType=FZIPType.RESTORE, status=FZIPStatus.RESTORE_CANCELED)
        # Subsequent checks can return latest from store
        return store.get(job_id, u)

    mock_service_get.side_effect = service_get

    # Start restore; the service should observe canceled and stop
    resp = ops.start_fzip_restore_handler({'pathParameters': {'jobId': restore_id}}, user_id, restore_id)
    assert resp['statusCode'] == 200

    # Final job state should be canceled with completedAt set
    final = store.get(restore_id, user_id)
    assert final is not None
    assert final.status == FZIPStatus.RESTORE_CANCELED
    assert final.completed_at is not None


