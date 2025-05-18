"""
Unit tests for authorization check functions.
"""
import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime

from models.account import Account, Currency, AccountType
from models.money import Money
from models.file_map import FileMap, FieldMapping
from models.transaction_file import TransactionFile, FileFormat, ProcessingStatus
from services.auth_checks import (
    checked_mandatory_account,
    checked_optional_account,
    checked_mandatory_transaction_file,
    checked_optional_transaction_file,
    checked_mandatory_file_map,
    checked_optional_file_map
)
from utils.auth import NotAuthorized, NotFound

class TestAuthChecks(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.user_id = "test_user_id"
        self.other_user_id = "other_user_id"
        
        # Sample account
        self.account = Account(
            account_id="test_account_id",
            user_id=self.user_id,
            account_name="Test Account",
            account_type=AccountType.CHECKING,
            institution="Test Bank",
            currency=Currency.USD,
            balance=Money(Decimal("1000.00"), Currency.USD),
            is_active=True
        )
        
        # Sample transaction file
        self.transaction_file = TransactionFile(
            file_id="test_file_id",
            user_id=self.user_id,
            account_id="test_account_id",
            file_format=FileFormat.CSV,
            file_map_id="test_map_id",
            opening_balance=Money(Decimal("1000.00"), Currency.USD),
            file_name="test.csv",
            upload_date=int(datetime.now().timestamp() * 1000),
            file_size=1000,
            s3_key="test/test.csv",
            processing_status=ProcessingStatus.PENDING
        )
        
        # Sample file map
        self.file_map = FileMap(
            file_map_id="test_map_id",
            user_id=self.user_id,
            name="Test Map",
            description="Test mapping configuration",
            mappings=[
                FieldMapping(source_field="Date", target_field="date"),
                FieldMapping(source_field="Description", target_field="description")
            ]
        )

    @patch('services.auth_checks.get_account')
    def test_checked_mandatory_account_success(self, mock_get_account):
        """Test successful mandatory account check."""
        mock_get_account.return_value = self.account
        
        result = checked_mandatory_account("test_account_id", self.user_id)
        self.assertEqual(result, self.account)
        mock_get_account.assert_called_once_with("test_account_id")

    @patch('services.auth_checks.get_account')
    def test_checked_mandatory_account_not_found(self, mock_get_account):
        """Test mandatory account check with non-existent account."""
        mock_get_account.return_value = None
        
        with self.assertRaises(NotFound):
            checked_mandatory_account("nonexistent_id", self.user_id)

    @patch('services.auth_checks.get_account')
    def test_checked_mandatory_account_unauthorized(self, mock_get_account):
        """Test mandatory account check with unauthorized user."""
        mock_get_account.return_value = self.account
        
        with self.assertRaises(NotAuthorized):
            checked_mandatory_account("test_account_id", self.other_user_id)

    @patch('services.auth_checks.get_account')
    def test_checked_optional_account_success(self, mock_get_account):
        """Test successful optional account check."""
        mock_get_account.return_value = self.account
        
        result = checked_optional_account("test_account_id", self.user_id)
        self.assertEqual(result, self.account)

    @patch('services.auth_checks.get_account')
    def test_checked_optional_account_none(self, mock_get_account):
        """Test optional account check with None account_id."""
        result = checked_optional_account(None, self.user_id)
        self.assertIsNone(result)
        mock_get_account.assert_not_called()

    @patch('services.auth_checks.get_account')
    def test_checked_optional_account_not_found(self, mock_get_account):
        """Test optional account check with non-existent account."""
        mock_get_account.return_value = None
        
        result = checked_optional_account("nonexistent_id", self.user_id)
        self.assertIsNone(result)

    @patch('services.auth_checks.get_transaction_file')
    def test_checked_mandatory_transaction_file_success(self, mock_get_file):
        """Test successful mandatory transaction file check."""
        mock_get_file.return_value = self.transaction_file
        
        result = checked_mandatory_transaction_file("test_file_id", self.user_id)
        self.assertEqual(result, self.transaction_file)
        mock_get_file.assert_called_once_with("test_file_id")

    @patch('services.auth_checks.get_transaction_file')
    def test_checked_mandatory_transaction_file_not_found(self, mock_get_file):
        """Test mandatory transaction file check with non-existent file."""
        mock_get_file.return_value = None
        
        with self.assertRaises(NotFound):
            checked_mandatory_transaction_file("nonexistent_id", self.user_id)

    @patch('services.auth_checks.get_transaction_file')
    def test_checked_mandatory_transaction_file_unauthorized(self, mock_get_file):
        """Test mandatory transaction file check with unauthorized user."""
        mock_get_file.return_value = self.transaction_file
        
        with self.assertRaises(NotAuthorized):
            checked_mandatory_transaction_file("test_file_id", self.other_user_id)

    @patch('services.auth_checks.get_transaction_file')
    def test_checked_optional_transaction_file_success(self, mock_get_file):
        """Test successful optional transaction file check."""
        mock_get_file.return_value = self.transaction_file
        
        result = checked_optional_transaction_file("test_file_id", self.user_id)
        self.assertEqual(result, self.transaction_file)

    @patch('services.auth_checks.get_transaction_file')
    def test_checked_optional_transaction_file_none(self, mock_get_file):
        """Test optional transaction file check with None file_id."""
        result = checked_optional_transaction_file(None, self.user_id)
        self.assertIsNone(result)
        mock_get_file.assert_not_called()

    @patch('services.auth_checks.get_file_map')
    def test_checked_mandatory_file_map_success(self, mock_get_map):
        """Test successful mandatory file map check."""
        mock_get_map.return_value = self.file_map
        
        result = checked_mandatory_file_map("test_map_id", self.user_id)
        self.assertEqual(result, self.file_map)
        mock_get_map.assert_called_once_with("test_map_id")

    @patch('services.auth_checks.get_file_map')
    def test_checked_mandatory_file_map_not_found(self, mock_get_map):
        """Test mandatory file map check with non-existent map."""
        mock_get_map.return_value = None
        
        with self.assertRaises(NotFound):
            checked_mandatory_file_map("nonexistent_id", self.user_id)

    @patch('services.auth_checks.get_file_map')
    def test_checked_mandatory_file_map_unauthorized(self, mock_get_map):
        """Test mandatory file map check with unauthorized user."""
        mock_get_map.return_value = self.file_map
        
        with self.assertRaises(NotAuthorized):
            checked_mandatory_file_map("test_map_id", self.other_user_id)

    @patch('services.auth_checks.get_file_map')
    def test_checked_optional_file_map_success(self, mock_get_map):
        """Test successful optional file map check."""
        mock_get_map.return_value = self.file_map
        
        result = checked_optional_file_map("test_map_id", self.user_id)
        self.assertEqual(result, self.file_map)

    @patch('services.auth_checks.get_file_map')
    def test_checked_optional_file_map_none(self, mock_get_map):
        """Test optional file map check with None map_id."""
        result = checked_optional_file_map(None, self.user_id)
        self.assertIsNone(result)
        mock_get_map.assert_not_called()

    @patch('services.auth_checks.get_file_map')
    def test_checked_optional_file_map_not_found(self, mock_get_map):
        """Test optional file map check with non-existent map."""
        mock_get_map.return_value = None
        
        result = checked_optional_file_map("nonexistent_id", self.user_id)
        self.assertIsNone(result) 