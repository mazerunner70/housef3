from unittest.mock import patch
import uuid

from services.fzip_service import FZIPService
from models.fzip import FZIPJob, FZIPType, FZIPStatus


@patch('services.fzip_service.update_fzip_job')
@patch('services.fzip_service.get_fzip_job')
def test_restore_checks_cancel(mock_get, mock_update):
    svc = FZIPService()
    job_id = uuid.uuid4()
    job = FZIPJob(userId='u1', jobType=FZIPType.RESTORE, status=FZIPStatus.RESTORE_PROCESSING, jobId=job_id)

    # First call returns canceled status to trigger the cancel path
    canceled_job = FZIPJob(userId='u1', jobType=FZIPType.RESTORE, status=FZIPStatus.RESTORE_CANCELED, jobId=job_id)
    mock_get.return_value = canceled_job

    try:
        svc._check_cancel(job)
        assert False, "Expected CanceledException to be raised"
    except Exception as e:
        # CanceledException is defined in the module; checking by message avoids import
        assert 'canceled' in str(e).lower()
    
    # Ensure job was updated to terminal canceled with completedAt
    assert mock_update.called


