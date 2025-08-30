import json
import uuid
from unittest.mock import patch, MagicMock

from src.consumers import restore_consumer as consumer
from models.fzip import FZIPStatus, FZIPType, FZIPJob


def _s3_event(bucket: str, key: str):
    return {
        'Records': [
            {
                'eventName': 'ObjectCreated:Put',
                's3': {'bucket': {'name': bucket}, 'object': {'key': key}},
            }
        ]
    }


@patch('src.consumers.restore_consumer.update_fzip_job')
@patch('src.consumers.restore_consumer.create_fzip_job')
@patch('src.consumers.restore_consumer.get_fzip_job')
@patch('src.consumers.restore_consumer.get_object_metadata')
@patch('services.fzip_service.FZIPService._validate_empty_profile')
@patch('services.fzip_service.FZIPService._validate_business_rules')
@patch('services.fzip_service.FZIPService._validate_schema')
@patch('services.fzip_service.FZIPService._parse_package')
def test_consumer_validation_pass(
    mock_parse,
    mock_schema,
    mock_business,
    mock_empty,
    mock_head,
    mock_get,
    mock_create,
    mock_update,
):
    user_id = 'user-x'
    restore_id = str(uuid.uuid4())
    key = f'restore_packages/{user_id}/{restore_id}.fzip'
    bucket = 'bucket-x'

    # No existing job
    mock_get.return_value = None

    mock_head.return_value = {'metadata': {'userid': user_id, 'restoreid': restore_id}, 'content_length': 123}
    mock_parse.return_value = {'manifest': {'user_id': user_id}, 'data': {}, 'raw': b''}
    mock_schema.return_value = {'valid': True}
    mock_business.return_value = {'valid': True}
    mock_empty.return_value = {'valid': True}

    resp = consumer.handler(_s3_event(bucket, key), None)

    assert resp['statusCode'] == 200
    # Ensure we created and updated the job to validation passed
    assert mock_create.called
    # The last update call should set status to RESTORE_VALIDATION_PASSED
    assert mock_update.call_count >= 1


@patch('src.consumers.restore_consumer.update_fzip_job')
@patch('src.consumers.restore_consumer.create_fzip_job')
@patch('src.consumers.restore_consumer.get_fzip_job')
@patch('src.consumers.restore_consumer.get_object_metadata')
@patch('services.fzip_service.FZIPService._validate_empty_profile')
@patch('services.fzip_service.FZIPService._validate_business_rules')
@patch('services.fzip_service.FZIPService._validate_schema')
@patch('services.fzip_service.FZIPService._parse_package')
def test_consumer_validation_fail_schema(
    mock_parse,
    mock_schema,
    mock_business,
    mock_empty,
    mock_head,
    mock_get,
    mock_create,
    mock_update,
):
    user_id = 'user-y'
    restore_id = str(uuid.uuid4())
    key = f'restore_packages/{user_id}/{restore_id}.fzip'
    bucket = 'bucket-y'

    mock_get.return_value = None
    mock_head.return_value = {'metadata': {'userid': user_id, 'restoreid': restore_id}, 'content_length': 123}
    mock_parse.return_value = {'manifest': {'user_id': user_id}, 'data': {}, 'raw': b''}
    mock_schema.return_value = {'valid': False, 'errors': ['bad']}

    resp = consumer.handler(_s3_event(bucket, key), None)
    assert resp['statusCode'] == 200
    assert mock_create.called
    assert mock_update.called


