import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from decimal import Decimal

from models.account import Account, AccountType, Currency
from models.file_map import FileMap, FieldMapping
from models.transaction_file import TransactionFile, ProcessingStatus
from models.money import Money
from services.auth_checks import (
    checked_mandatory_account,
    checked_optional_account,
    checked_mandatory_transaction_file,
    checked_optional_transaction_file,
    checked_mandatory_file_map,
    checked_optional_file_map,
)
from utils.auth import NotAuthorized, NotFound

class TestAuthChecks(unittest.TestCase):
    def setUp(self):
        self.user_id = "test_user_123"
        self.other_user_id = "other_user_456"
        
        # Mock account
        self.account = Account(
            account_id="acc_123",
            user_id=self.user_id,
            account_name="Test Account",
            account_type=AccountType.CHECKING,
            institution="Test Bank",
            balance=Money(amount=Decimal('100.00'), currency=Currency.USD),
            currency=Currency.USD
        )
        
        # Mock transaction file
        self.transaction_file = TransactionFile(
            file_id="file_123",
            user_id=self.user_id,
            file_name="test.csv",
            upload_date=int(datetime.now().timestamp() * 1000),
            file_size=1024,
            s3_key="test/test.csv",
            processing_status=ProcessingStatus.PENDING
        )
        
        # Mock file map
        self.file_map = FileMap(
            file_map_id="map_123",
            user_id=self.user_id,
            name="Test Map",
            mappings=[
                FieldMapping(source_field="Date", target_field="transaction_date"),
                FieldMapping(source_field="Amount", target_field="amount")
            ]
        )

    @patch('services.auth_checks.get_account')
    def test_checked_mandatory_account_success(self, mock_get_account):
        mock_get_account.return_value = self.account
        result = checked_mandatory_account("acc_123", self.user_id)
        self.assertEqual(result, self.account)
        mock_get_account.assert_called_once_with("acc_123")

    @patch('services.auth_checks.get_account')
    def test_checked_mandatory_account_not_found(self, mock_get_account):
        mock_get_account.return_value = None
        with self.assertRaises(NotFound):
            checked_mandatory_account("acc_123", self.user_id)

    @patch('services.auth_checks.get_account')
    def test_checked_mandatory_account_not_authorized(self, mock_get_account):
        mock_get_account.return_value = self.account
        with self.assertRaises(NotAuthorized):
            checked_mandatory_account("acc_123", self.other_user_id)

    @patch('services.auth_checks.get_account')
    def test_checked_optional_account_success(self, mock_get_account):
        mock_get_account.return_value = self.account
        result = checked_optional_account("acc_123", self.user_id)
        self.assertEqual(result, self.account)

    @patch('services.auth_checks.get_account')
    def test_checked_optional_account_none_input(self, mock_get_account):
        result = checked_optional_account(None, self.user_id)
        self.assertIsNone(result)
        mock_get_account.assert_not_called()

    @patch('services.auth_checks.get_account')
    def test_checked_optional_account_not_found(self, mock_get_account):
        mock_get_account.return_value = None
        result = checked_optional_account("acc_123", self.user_id)
        self.assertIsNone(result)

    @patch('services.auth_checks.get_transaction_file')
    def test_checked_mandatory_transaction_file_success(self, mock_get_file):
        mock_get_file.return_value = self.transaction_file
        result = checked_mandatory_transaction_file("file_123", self.user_id)
        self.assertEqual(result, self.transaction_file)

    @patch('services.auth_checks.get_transaction_file')
    def test_checked_mandatory_transaction_file_not_found(self, mock_get_file):
        mock_get_file.return_value = None
        with self.assertRaises(NotFound):
            checked_mandatory_transaction_file("file_123", self.user_id)

    @patch('services.auth_checks.get_transaction_file')
    def test_checked_mandatory_transaction_file_not_authorized(self, mock_get_file):
        mock_get_file.return_value = self.transaction_file
        with self.assertRaises(NotAuthorized):
            checked_mandatory_transaction_file("file_123", self.other_user_id)

    @patch('services.auth_checks.get_transaction_file')
    def test_checked_optional_transaction_file_success(self, mock_get_file):
        mock_get_file.return_value = self.transaction_file
        result = checked_optional_transaction_file("file_123", self.user_id)
        self.assertEqual(result, self.transaction_file)

    @patch('services.auth_checks.get_transaction_file')
    def test_checked_optional_transaction_file_none_input(self, mock_get_file):
        result = checked_optional_transaction_file(None, self.user_id)
        self.assertIsNone(result)
        mock_get_file.assert_not_called()

    @patch('services.auth_checks.get_transaction_file')
    def test_checked_optional_transaction_file_not_found(self, mock_get_file):
        mock_get_file.return_value = None
        result = checked_optional_transaction_file("file_123", self.user_id)
        self.assertIsNone(result)

    @patch('services.auth_checks.get_file_map')
    def test_checked_mandatory_file_map_success(self, mock_get_map):
        mock_get_map.return_value = self.file_map
        result = checked_mandatory_file_map("map_123", self.user_id)
        self.assertEqual(result, self.file_map)

    @patch('services.auth_checks.get_file_map')
    def test_checked_mandatory_file_map_not_found(self, mock_get_map):
        mock_get_map.return_value = None
        with self.assertRaises(NotFound):
            checked_mandatory_file_map("map_123", self.user_id)

    @patch('services.auth_checks.get_file_map')
    def test_checked_mandatory_file_map_not_authorized(self, mock_get_map):
        mock_get_map.return_value = self.file_map
        with self.assertRaises(NotAuthorized):
            checked_mandatory_file_map("map_123", self.other_user_id)

    @patch('services.auth_checks.get_file_map')
    def test_checked_optional_file_map_success(self, mock_get_map):
        mock_get_map.return_value = self.file_map
        result = checked_optional_file_map("map_123", self.user_id)
        self.assertEqual(result, self.file_map)

    @patch('services.auth_checks.get_file_map')
    def test_checked_optional_file_map_none_input(self, mock_get_map):
        result = checked_optional_file_map(None, self.user_id)
        self.assertIsNone(result)
        mock_get_map.assert_not_called()

    @patch('services.auth_checks.get_file_map')
    def test_checked_optional_file_map_not_found(self, mock_get_map):
        mock_get_map.return_value = None
        result = checked_optional_file_map("map_123", self.user_id)
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main() 