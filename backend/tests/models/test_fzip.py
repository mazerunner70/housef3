"""
Unit tests for FZIP models, specifically testing DynamoDB item conversion.
"""
import unittest
import uuid
from datetime import datetime, timezone

from models.fzip import FZIPJob, FZIPStatus, FZIPType, FZIPBackupType, FZIPFormat


class TestFZIPJobDynamoDBConversion(unittest.TestCase):
    """Test FZIPJob conversion from DynamoDB items"""
    
    def test_from_dynamodb_item_converts_string_enums_properly(self):
        """Test that string enum values from DynamoDB are properly converted to enum objects"""
        # Mock DynamoDB item with string enum values (as they would come from DynamoDB)
        dynamodb_item = {
            'jobId': str(uuid.uuid4()),
            'userId': 'test-user-123',
            'jobType': 'backup',  # String value from DynamoDB
            'status': 'backup_completed',  # String value from DynamoDB
            'backupType': 'complete',  # String value from DynamoDB
            'packageFormat': 'fzip',  # String value from DynamoDB
            'createdAt': int(datetime.now(timezone.utc).timestamp() * 1000),
            'progress': 100,
            'includeAnalytics': False
        }
        
        # Convert from DynamoDB item
        fzip_job = FZIPJob.from_dynamodb_item(dynamodb_item)
        
        # Assert that string values were properly converted to enum objects
        self.assertIsInstance(fzip_job.job_type, FZIPType, 
                            f"job_type should be FZIPType enum, got {type(fzip_job.job_type)}")
        self.assertEqual(fzip_job.job_type, FZIPType.BACKUP)
        
        self.assertIsInstance(fzip_job.status, FZIPStatus,
                            f"status should be FZIPStatus enum, got {type(fzip_job.status)}")
        self.assertEqual(fzip_job.status, FZIPStatus.BACKUP_COMPLETED)
        
        self.assertIsInstance(fzip_job.backup_type, FZIPBackupType,
                            f"backup_type should be FZIPBackupType enum, got {type(fzip_job.backup_type)}")
        self.assertEqual(fzip_job.backup_type, FZIPBackupType.COMPLETE)
        
        self.assertIsInstance(fzip_job.package_format, FZIPFormat,
                            f"package_format should be FZIPFormat enum, got {type(fzip_job.package_format)}")
        self.assertEqual(fzip_job.package_format, FZIPFormat.FZIP)
        
        # Test that .value property works (this is what was failing before)
        self.assertEqual(fzip_job.job_type.value, 'backup')
        self.assertEqual(fzip_job.status.value, 'backup_completed')
        self.assertEqual(fzip_job.backup_type.value, 'complete')
        self.assertEqual(fzip_job.package_format.value, 'fzip')
        
    def test_from_dynamodb_item_handles_restore_job(self):
        """Test conversion of restore job with restore-specific enum values"""
        dynamodb_item = {
            'jobId': str(uuid.uuid4()),
            'userId': 'test-user-456',
            'jobType': 'restore',  # String value from DynamoDB
            'status': 'restore_processing',  # String value from DynamoDB
            'packageFormat': 'fzip',
            'createdAt': int(datetime.now(timezone.utc).timestamp() * 1000),
            'progress': 50,
            'includeAnalytics': False
        }
        
        fzip_job = FZIPJob.from_dynamodb_item(dynamodb_item)
        
        # Verify enum conversions
        self.assertIsInstance(fzip_job.job_type, FZIPType)
        self.assertEqual(fzip_job.job_type, FZIPType.RESTORE)
        
        self.assertIsInstance(fzip_job.status, FZIPStatus)
        self.assertEqual(fzip_job.status, FZIPStatus.RESTORE_PROCESSING)
        
        # Test .value access works
        self.assertEqual(fzip_job.job_type.value, 'restore')
        self.assertEqual(fzip_job.status.value, 'restore_processing')
        
    def test_from_dynamodb_item_handles_none_backup_type(self):
        """Test that None backup_type is handled properly"""
        dynamodb_item = {
            'jobId': str(uuid.uuid4()),
            'userId': 'test-user-789',
            'jobType': 'backup',
            'status': 'backup_initiated',
            'packageFormat': 'fzip',
            'createdAt': int(datetime.now(timezone.utc).timestamp() * 1000),
            'progress': 0,
            'includeAnalytics': False,
            'backupType': None  # This should remain None
        }
        
        fzip_job = FZIPJob.from_dynamodb_item(dynamodb_item)
        
        # Verify backup_type is None and doesn't cause issues
        self.assertIsNone(fzip_job.backup_type)
        
    def test_enum_conversion_success_verification(self):
        """Test that verifies enum conversion works properly and .value access succeeds"""
        dynamodb_item = {
            'jobId': str(uuid.uuid4()),
            'userId': 'test-user-999',
            'jobType': 'backup',
            'status': 'backup_completed',
            'backupType': 'complete',
            'packageFormat': 'fzip',
            'createdAt': int(datetime.now(timezone.utc).timestamp() * 1000),
            'progress': 100,
            'includeAnalytics': False
        }
        
        fzip_job = FZIPJob.from_dynamodb_item(dynamodb_item)
        
        # Verify that enum conversion worked properly - these should all be enum objects
        # Note: Since our enums inherit from str, isinstance(enum, str) returns True
        # So we check the actual type instead
        self.assertEqual(type(fzip_job.job_type).__name__, 'FZIPType', 
                        f"job_type should be FZIPType enum, got {type(fzip_job.job_type)}")
        self.assertEqual(type(fzip_job.status).__name__, 'FZIPStatus',
                        f"status should be FZIPStatus enum, got {type(fzip_job.status)}")
        self.assertEqual(type(fzip_job.backup_type).__name__, 'FZIPBackupType',
                        f"backup_type should be FZIPBackupType enum, got {type(fzip_job.backup_type)}")
        self.assertEqual(type(fzip_job.package_format).__name__, 'FZIPFormat',
                        f"package_format should be FZIPFormat enum, got {type(fzip_job.package_format)}")
                
        # The correct behavior: these should work because they are proper enum objects
        self.assertIsNotNone(fzip_job.job_type.value)
        self.assertIsNotNone(fzip_job.status.value)
        if fzip_job.backup_type:  # Only check if not None
            self.assertIsNotNone(fzip_job.backup_type.value)
        self.assertIsNotNone(fzip_job.package_format.value)
        
        # Verify the actual values are correct
        self.assertEqual(fzip_job.job_type.value, 'backup')
        self.assertEqual(fzip_job.status.value, 'backup_completed')
        self.assertEqual(fzip_job.backup_type.value, 'complete')
        self.assertEqual(fzip_job.package_format.value, 'fzip')

    def test_json_and_dynamodb_serialization_restore_canceled(self):
        """Test JSON and DynamoDB serialization for RESTORE_CANCELED status."""
        job = FZIPJob(
            jobId=uuid.uuid4(),
            userId='user-abc',
            jobType=FZIPType.RESTORE,
            status=FZIPStatus.RESTORE_CANCELED,
            packageFormat=FZIPFormat.FZIP
        )

        # model_dump should serialize enums to their values due to use_enum_values=True
        dumped = job.model_dump(by_alias=True)
        self.assertEqual(dumped['status'], 'restore_canceled')
        self.assertEqual(dumped['jobType'], 'restore')
        self.assertEqual(dumped['packageFormat'], 'fzip')

        # to_dynamodb_item should also serialize to strings
        ddb_item = job.to_dynamodb_item()
        self.assertEqual(ddb_item['status'], 'restore_canceled')
        self.assertEqual(ddb_item['jobType'], 'restore')
        self.assertEqual(ddb_item['packageFormat'], 'fzip')

        # Round trip back to model
        round_trip = FZIPJob.from_dynamodb_item(ddb_item)
        self.assertIsInstance(round_trip.status, FZIPStatus)
        self.assertEqual(round_trip.status, FZIPStatus.RESTORE_CANCELED)
        self.assertEqual(round_trip.status.value, 'restore_canceled')


if __name__ == '__main__':
    unittest.main()