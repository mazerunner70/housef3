"""
Unit tests for file service.
"""
import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime

from models.transaction_file import TransactionFile, FileFormat, ProcessingStatus, Currency
from models.money import Money
from models.file_map import FileMap
from services.file_service import get_files_for_user, get_files_for_account, format_file_metadata

class TestFileService(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.user_id = "test_user_id"
        self.account_id = "test_account_id"
        
        # Sample transaction file
        self.transaction_file = TransactionFile(
            file_id="test_file_id",
            user_id=self.user_id,
            account_id=self.account_id,
            file_format=FileFormat.CSV,
            file_map_id="test_map_id",
            opening_balance=Money(Decimal("1000.00"), Currency.USD),
            file_name="test.csv",
            upload_date=int(datetime.now().timestamp() * 1000),
            file_size=1000,
            s3_key="test/test.csv",
            processing_status=ProcessingStatus.PENDING,
            currency=Currency.USD,
            record_count=10
        )

        # Sample file map
        self.file_map = FileMap(
            file_map_id="test_map_id",
            user_id=self.user_id,
            name="Test Map",
            description="Test mapping configuration",
            mappings=[]
        )

    @patch('services.file_service.list_account_files')
    @patch('services.file_service.list_user_files')
    def test_get_files_for_user_with_account(self, mock_list_user, mock_list_account):
        """Test getting files for user with account ID filter."""
        mock_list_account.return_value = [self.transaction_file]
        
        result = get_files_for_user(self.user_id, self.account_id)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].file_id, "test_file_id")
        mock_list_account.assert_called_once_with(self.account_id)
        mock_list_user.assert_not_called()

    @patch('services.file_service.list_user_files')
    def test_get_files_for_user_without_account(self, mock_list_user):
        """Test getting files for user without account ID filter."""
        mock_list_user.return_value = [self.transaction_file]
        
        result = get_files_for_user(self.user_id)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].file_id, "test_file_id")
        mock_list_user.assert_called_once_with(self.user_id)

    @patch('services.file_service.list_account_files')
    def test_get_files_for_account(self, mock_list_account):
        """Test getting files for an account."""
        mock_list_account.return_value = [self.transaction_file]
        
        result = get_files_for_account(self.account_id)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].file_id, "test_file_id")
        mock_list_account.assert_called_once_with(self.account_id)

    @patch('services.file_service.get_file_map')
    def test_format_file_metadata_with_map(self, mock_get_map):
        """Test formatting file metadata with file map."""
        mock_get_map.return_value = self.file_map
        
        result = format_file_metadata(self.transaction_file)
        
        # Check basic fields
        self.assertEqual(result['fileId'], "test_file_id")
        self.assertEqual(result['userId'], self.user_id)
        self.assertEqual(result['accountId'], self.account_id)
        self.assertEqual(result['fileFormat'], FileFormat.CSV)
        self.assertEqual(result['processingStatus'], ProcessingStatus.PENDING)
        self.assertEqual(result['recordCount'], 10)
        
        # Check money fields
        self.assertEqual(result['openingBalance'].amount, Decimal("1000.00"))
        self.assertEqual(result['openingBalance'].currency, Currency.USD)
        
        # Check file map fields
        self.assertIn('fieldMap', result)
        self.assertEqual(result['fieldMap']['fieldMapId'], "test_map_id")
        self.assertEqual(result['fieldMap']['name'], "Test Map")
        self.assertEqual(result['fieldMap']['description'], "Test mapping configuration")

    @patch('services.file_service.get_file_map')
    def test_format_file_metadata_without_map(self, mock_get_map):
        """Test formatting file metadata without file map."""
        mock_get_map.return_value = None
        self.transaction_file.file_map_id = None
        
        result = format_file_metadata(self.transaction_file)
        
        # Check basic fields are present
        self.assertEqual(result['fileId'], "test_file_id")
        self.assertEqual(result['userId'], self.user_id)
        self.assertEqual(result['accountId'], self.account_id)
        
        # Check file map is not present
        self.assertNotIn('fieldMap', result)

    def test_format_file_metadata_optional_fields(self):
        """Test formatting file metadata handles optional fields correctly."""
        # Create a file without optional fields
        minimal_file = TransactionFile(
            file_id="test_file_id",
            user_id=self.user_id,
            file_name="test.csv" ,
            upload_date=int(datetime.now().timestamp() * 1000),
            file_size=1000,
            s3_key="test/test.csv",
            processing_status=ProcessingStatus.PENDING
        )
        
        result = format_file_metadata(minimal_file)
        
        # Check required fields
        self.assertEqual(result['fileId'], "test_file_id")
        self.assertEqual(result['userId'], self.user_id)
        
        # Check optional fields are not present
        self.assertNotIn('openingBalance', result)
        self.assertNotIn('fieldMap', result)
        self.assertNotIn('accountId', result) 
        self.assertNotIn('fileFormat', result)
        self.assertNotIn('recordCount', result) 