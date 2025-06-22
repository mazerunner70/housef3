"""
Unit tests for TransactionFile serialization and deserialization.
"""
import unittest
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from models.transaction_file import TransactionFile, DateRange, FileFormat, ProcessingStatus
from models.account import Currency


class TestTransactionFileSerialization(unittest.TestCase):
    """Test serialization and deserialization of TransactionFile objects."""

    def setUp(self):
        """Set up test data."""
        self.test_file_id = uuid.uuid4()
        self.test_account_id = uuid.uuid4()
        self.test_file_map_id = uuid.uuid4()
        self.test_user_id = "test-user-123"
        
        # Create a test DateRange
        self.test_date_range = DateRange(
            startDate=1707523200000,  # 2024-02-10
            endDate=1729987200000     # 2024-10-27
        )
        
        # Create a complete TransactionFile using aliases (camelCase)
        self.transaction_file = TransactionFile(
            userId=self.test_user_id,
            fileName="test_mbna_statement.qif",
            fileSize=12345,
            s3Key=f"{self.test_user_id}/{self.test_file_id}/test_mbna_statement.qif",
            processingStatus=ProcessingStatus.PROCESSED,
            processedDate=int(datetime.now(timezone.utc).timestamp() * 1000),
            fileFormat=FileFormat.QIF,
            accountId=self.test_account_id,
            fileMapId=self.test_file_map_id,
            recordCount=25,
            dateRange=self.test_date_range,
            openingBalance=Decimal("1234.56"),
            currency=Currency.CAD,
            duplicateCount=2,
            transactionCount=23
        )

    def test_date_range_serialization(self):
        """Test that DateRange serializes to a simple dict structure."""
        # Test DateRange serialization directly
        date_range_dict = self.test_date_range.model_dump(by_alias=True)
        
        expected = {
            "startDate": 1707523200000,
            "endDate": 1729987200000
        }
        
        self.assertEqual(date_range_dict, expected)
        self.assertIsInstance(date_range_dict["startDate"], int)
        self.assertIsInstance(date_range_dict["endDate"], int)

    def test_date_range_deserialization(self):
        """Test that DateRange can be reconstructed from a simple dict."""
        # Test data as it should come from DynamoDB (simple dict)
        simple_dict = {
            "startDate": 1707523200000,
            "endDate": 1729987200000
        }
        
        # Reconstruct DateRange
        reconstructed = DateRange.model_validate(simple_dict)
        
        self.assertEqual(reconstructed.start_date, 1707523200000)
        self.assertEqual(reconstructed.end_date, 1729987200000)

    def test_transaction_file_to_dynamodb_item(self):
        """Test that TransactionFile serializes to a simple dict structure for DynamoDB."""
        dynamodb_item = self.transaction_file.to_dynamodb_item()
        
        # Check that dateRange is a simple dict, not DynamoDB type descriptors
        self.assertIn("dateRange", dynamodb_item)
        date_range = dynamodb_item["dateRange"]
        
        # Should be a simple dict
        self.assertIsInstance(date_range, dict)
        
        # Should have the correct structure
        expected_date_range = {
            "startDate": 1707523200000,
            "endDate": 1729987200000
        }
        self.assertEqual(date_range, expected_date_range)
        
        # Values should be plain integers, not DynamoDB type descriptors
        self.assertIsInstance(date_range["startDate"], int)
        self.assertIsInstance(date_range["endDate"], int)
        
        # Verify other fields are correctly serialized
        self.assertEqual(dynamodb_item["fileId"], str(self.transaction_file.file_id))
        self.assertEqual(dynamodb_item["userId"], self.test_user_id)
        self.assertEqual(dynamodb_item["processingStatus"], "processed")
        self.assertEqual(dynamodb_item["fileFormat"], "qif")
        self.assertEqual(dynamodb_item["currency"], "CAD")
        self.assertEqual(dynamodb_item["openingBalance"], "1234.56")

    def test_transaction_file_from_dynamodb_item_simple_dict(self):
        """Test that TransactionFile can be reconstructed from a simple dict structure."""
        # Simulate data as it should come from DynamoDB (simple dict structure)
        dynamodb_data = {
            "fileId": str(self.test_file_id),
            "userId": self.test_user_id,
            "fileName": "test_mbna_statement.qif",
            "fileSize": 12345,
            "s3Key": f"{self.test_user_id}/{self.test_file_id}/test_mbna_statement.qif",
            "processingStatus": "processed",
            "fileFormat": "qif",
            "accountId": str(self.test_account_id),
            "fileMapId": str(self.test_file_map_id),
            "recordCount": 25,
            "dateRange": {
                "startDate": 1707523200000,
                "endDate": 1729987200000
            },
            "openingBalance": "1234.56",
            "currency": "CAD",
            "duplicateCount": 2,
            "transactionCount": 23,
            "uploadDate": int(datetime.now(timezone.utc).timestamp() * 1000),
            "processedDate": int(datetime.now(timezone.utc).timestamp() * 1000),
            "createdAt": int(datetime.now(timezone.utc).timestamp() * 1000),
            "updatedAt": int(datetime.now(timezone.utc).timestamp() * 1000)
        }
        
        # Reconstruct TransactionFile
        reconstructed = TransactionFile.from_dynamodb_item(dynamodb_data)
        
        # Verify the DateRange was properly reconstructed
        self.assertIsNotNone(reconstructed.date_range)
        self.assertIsInstance(reconstructed.date_range, DateRange)
        assert reconstructed.date_range is not None  # Type assertion for linter
        self.assertEqual(reconstructed.date_range.start_date, 1707523200000)
        self.assertEqual(reconstructed.date_range.end_date, 1729987200000)
        
        # Verify other fields
        self.assertEqual(reconstructed.file_id, self.test_file_id)
        self.assertEqual(reconstructed.user_id, self.test_user_id)
        self.assertEqual(reconstructed.processing_status, ProcessingStatus.PROCESSED)
        self.assertEqual(reconstructed.file_format, FileFormat.QIF)
        self.assertEqual(reconstructed.currency, Currency.CAD)
        self.assertEqual(reconstructed.opening_balance, Decimal("1234.56"))

    def test_transaction_file_from_dynamodb_item_with_type_descriptors(self):
        """Test that TransactionFile can handle DynamoDB type descriptors (if they somehow appear)."""
        # Simulate data with DynamoDB type descriptors (the problematic format)
        dynamodb_data_with_types = {
            "fileId": str(self.test_file_id),
            "userId": self.test_user_id,
            "fileName": "test_mbna_statement.qif",
            "fileSize": 12345,
            "s3Key": f"{self.test_user_id}/{self.test_file_id}/test_mbna_statement.qif",
            "processingStatus": "processed",
            "fileFormat": "qif",
            "accountId": str(self.test_account_id),
            "fileMapId": str(self.test_file_map_id),
            "recordCount": 25,
            "dateRange": {
                "startDate": {"N": "1707523200000"},
                "endDate": {"N": "1729987200000"}
            },
            "openingBalance": "1234.56",
            "currency": "CAD",
            "duplicateCount": 2,
            "transactionCount": 23,
            "uploadDate": int(datetime.now(timezone.utc).timestamp() * 1000),
            "processedDate": int(datetime.now(timezone.utc).timestamp() * 1000),
            "createdAt": int(datetime.now(timezone.utc).timestamp() * 1000),
            "updatedAt": int(datetime.now(timezone.utc).timestamp() * 1000)
        }
        
        # With our type descriptor handling, this should now work properly
        reconstructed = TransactionFile.from_dynamodb_item(dynamodb_data_with_types)
        
        # Verify the DateRange was properly reconstructed from type descriptors
        self.assertIsNotNone(reconstructed.date_range)
        self.assertIsInstance(reconstructed.date_range, DateRange)
        assert reconstructed.date_range is not None  # Type assertion for linter
        self.assertEqual(reconstructed.date_range.start_date, 1707523200000)
        self.assertEqual(reconstructed.date_range.end_date, 1729987200000)
        
        # Verify other fields are also correct
        self.assertEqual(reconstructed.processing_status, ProcessingStatus.PROCESSED)
        self.assertEqual(reconstructed.file_format, FileFormat.QIF)

    def test_round_trip_serialization(self):
        """Test complete round-trip serialization: object -> dict -> object."""
        # Serialize to DynamoDB format
        dynamodb_item = self.transaction_file.to_dynamodb_item()
        
        # Deserialize back to object
        reconstructed = TransactionFile.from_dynamodb_item(dynamodb_item)
        
        # Verify the round trip preserves the DateRange
        self.assertIsNotNone(reconstructed.date_range)
        assert reconstructed.date_range is not None  # Type assertion for linter
        self.assertEqual(reconstructed.date_range.start_date, self.test_date_range.start_date)
        self.assertEqual(reconstructed.date_range.end_date, self.test_date_range.end_date)
        
        # Verify other key fields
        self.assertEqual(reconstructed.file_id, self.transaction_file.file_id)
        self.assertEqual(reconstructed.processing_status, self.transaction_file.processing_status)
        self.assertEqual(reconstructed.opening_balance, self.transaction_file.opening_balance)


if __name__ == '__main__':
    unittest.main() 