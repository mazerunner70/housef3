import json
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from models.fzip import FZIPStatus, FZIPType, FZIPJob
from src.handlers import fzip_operations as ops


def _auth_headers():
    return {
        'headers': {'Authorization': 'Bearer test'},
        'requestContext': {
            'authorizer': {
                'jwt': {
                    'claims': {
                        'sub': 'test-user-id',
                        'email': 'test@example.com',
                        'auth_time': '2024-01-01T00:00:00Z',
                    }
                }
            }
        },
    }


@patch('src.handlers.fzip_operations.get_presigned_post_url')
def test_post_restore_upload_url_success(mock_presigned):
    mock_presigned.return_value = {
        'url': 'https://s3.amazonaws.com/bucket',
        'fields': {
            'key': 'restore_packages/test-user-id/abc.fzip',
            'x-amz-meta-userid': 'test-user-id',
            'x-amz-meta-restoreid': 'abc',
            'x-amz-server-side-encryption': 'AES256',
        },
    }

    event = {
        **_auth_headers(),
        'routeKey': 'POST /fzip/restore/upload-url',
    }

    resp = ops.handler(event, None)
    assert resp['statusCode'] == 200
    body = json.loads(resp['body'])
    assert 'restoreId' in body
    assert 'url' in body and 'fields' in body
    # Diagnostics: ensure policy fields include encryption and metadata
    assert body['fields'].get('x-amz-server-side-encryption') == 'AES256'
    assert 'x-amz-meta-userid' in body['fields']
    assert 'x-amz-meta-restoreid' in body['fields']


@patch('src.handlers.fzip_operations.get_presigned_post_url')
def test_post_restore_upload_url_builds_correct_policy(mock_presigned):
    mock_presigned.return_value = {
        'url': 'https://s3.amazonaws.com/bucket',
        'fields': {'key': 'restore_packages/test-user-id/x.fzip'},
    }

    event = {
        **_auth_headers(),
        'routeKey': 'POST /fzip/restore/upload-url',
    }

    resp = ops.handler(event, None)
    assert resp['statusCode'] == 200

    # Verify policy conditions passed to S3 DAO
    assert mock_presigned.called
    _, kwargs = mock_presigned.call_args
    conditions = kwargs.get('conditions', [])

    # Must include content-length-range in array form
    assert any(isinstance(c, list) and c[0] == 'content-length-range' for c in conditions)

    # Must lock exact key using eq
    assert any(isinstance(c, list) and c[0] == 'eq' and c[1] == '$key' for c in conditions)

    # Must include SSE requirement to satisfy bucket policy
    assert any(isinstance(c, dict) and c.get('x-amz-server-side-encryption') == 'AES256' for c in conditions)


@patch('src.handlers.fzip_operations.update_fzip_job')
@patch('src.handlers.fzip_operations.get_fzip_job')
def test_cancel_restore_handler_success(mock_get, mock_update):
    # Build a non-terminal job
    job = FZIPJob(
        userId='test-user-id',
        jobType=FZIPType.RESTORE,
        status=FZIPStatus.RESTORE_PROCESSING,
    )
    mock_get.return_value = job

    event = {
        **_auth_headers(),
        'routeKey': 'POST /fzip/restore/{jobId}/cancel',
        'pathParameters': {'jobId': str(job.job_id)},
    }

    resp = ops.handler(event, None)
    assert resp['statusCode'] == 200
    body = json.loads(resp['body'])
    assert body['status'] == 'restore_canceled'
    assert body['jobId'] == str(job.job_id)
    mock_update.assert_called_once()


@patch('src.handlers.fzip_operations.update_fzip_job')
@patch('src.handlers.fzip_operations.get_fzip_job')
def test_cancel_restore_handler_rejects_terminal(mock_get, mock_update):
    job = FZIPJob(
        userId='test-user-id',
        jobType=FZIPType.RESTORE,
        status=FZIPStatus.RESTORE_COMPLETED,
    )
    mock_get.return_value = job

    event = {
        **_auth_headers(),
        'routeKey': 'POST /fzip/restore/{jobId}/cancel',
        'pathParameters': {'jobId': str(job.job_id)},
    }

    resp = ops.handler(event, None)
    assert resp['statusCode'] == 400
    body = json.loads(resp['body'])
    assert 'terminal' in body['error']
    mock_update.assert_not_called()


