"""
Unit tests for file processor service.
"""
import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime
from typing import cast

from models.account import Account, Currency, AccountType
from models.money import Money
from models.file_map import FileMap, FieldMapping
from models.transaction import Transaction
from models.transaction_file import TransactionFile, FileFormat, ProcessingStatus
from services.file_processor_service import (
    FileProcessorResponse,
    prepare_file_processing,
    determine_file_format,
    determine_file_map,
    parse_file_transactions,
    calculate_running_balances,
    save_transactions,
    update_file_status,
    update_transaction_duplicates,
    determine_opening_balances_from_transaction_overlap,
    process_new_file,
    update_file_mapping,
    update_opening_balance,
    change_file_account,
    process_file
)
from utils.auth import NotAuthorized, NotFound

class TestFileProcessorService(unittest.TestCase):
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
            processing_status=ProcessingStatus.PENDING,
            currency=Currency.USD
        )
        
        # Sample file map
        self.file_map = FileMap(
            file_map_id="test_map_id",
            user_id=self.user_id,
            name="Test Map",
            description="Test mapping configuration",
            mappings=[
                FieldMapping(source_field="Date", target_field="date"),
                FieldMapping(source_field="Description", target_field="description"),
                FieldMapping(source_field="Amount", target_field="amount")
            ]
        )
        
        # Sample transactions
        self.transactions = [
            Transaction.create(
                account_id="test_account_id",
                user_id=self.user_id,
                file_id="test_file_id",
                date=int(datetime.now().timestamp() * 1000),
                description="Test Transaction 1",
                amount=Money(Decimal("-50.00"), Currency.USD),
                balance=Money(Decimal("950.00"), Currency.USD),
                import_order=1
            ),
            Transaction.create(
                account_id="test_account_id",
                user_id=self.user_id,
                file_id="test_file_id",
                date=int(datetime.now().timestamp() * 1000),
                description="Test Transaction 2",
                amount=Money(Decimal("-30.00"), Currency.USD),
                balance=Money(Decimal("920.00"), Currency.USD),
                import_order=2
            )
        ]

    @patch('services.file_processor_service.checked_mandatory_transaction_file')
    def test_prepare_file_processing_success(self, mock_check_file):
        """Test successful file preparation."""
        mock_check_file.return_value = self.transaction_file
        
        result = prepare_file_processing("test_file_id", self.user_id)
        self.assertEqual(result, self.transaction_file)
        mock_check_file.assert_called_once_with("test_file_id", self.user_id)

    @patch('services.file_processor_service.checked_mandatory_transaction_file')
    def test_prepare_file_processing_unauthorized(self, mock_check_file):
        """Test file preparation with unauthorized user."""
        mock_check_file.side_effect = NotAuthorized("Not authorized")
        
        with self.assertRaises(NotAuthorized):
            prepare_file_processing("test_file_id", self.other_user_id)

    @patch('services.file_processor_service.file_type_selector')
    @patch('services.file_processor_service.update_transaction_file')
    def test_determine_file_format_detect(self, mock_update_file, mock_selector):
        """Test file format detection."""
        test_file = self.transaction_file
        test_file.file_format = None
        mock_selector.return_value = FileFormat.CSV
        
        result = determine_file_format(test_file, b"test content")
        self.assertEqual(result.file_format, FileFormat.CSV)
        mock_selector.assert_called_once_with(b"test content")
        mock_update_file.assert_called_once()

    @patch('services.file_processor_service.checked_optional_file_map')
    @patch('services.file_processor_service.checked_mandatory_account')
    def test_determine_file_map_from_file(self, mock_check_account, mock_check_map):
        """Test file map determination from file."""
        mock_check_map.return_value = self.file_map
        
        result = determine_file_map(self.transaction_file)
        self.assertEqual(result, self.file_map)
        mock_check_map.assert_called_once_with("test_map_id", self.user_id)

    def test_calculate_running_balances(self):
        """Test running balance calculation."""
        opening_balance = Money(Decimal("1000.00"), Currency.USD)
        transactions = [
            Transaction.create(
                account_id="test_account_id",
                user_id=self.user_id,
                file_id="test_file_id",
                date=int(datetime.now().timestamp() * 1000),
                description="Test Transaction",
                amount=Money(Decimal("-50.00"), Currency.USD),
                balance=None,
                import_order=1
            )
        ]
        
        calculate_running_balances(transactions, opening_balance)
        self.assertEqual(transactions[0].balance, Money(Decimal("950.00"), Currency.USD))

    @patch('services.file_processor_service.create_transaction')
    @patch('services.file_processor_service.checked_mandatory_account')
    @patch('services.file_processor_service.checked_mandatory_transaction_file')
    @patch('services.file_processor_service.update_transaction_file')
    def test_save_transactions(self, mock_update_file, mock_check_file, mock_check_account, mock_create_tx):
        """Test transaction saving."""
        mock_check_account.return_value = self.account
        mock_check_file.return_value = self.transaction_file
        mock_update_file.return_value = self.transaction_file
        
        transaction_count, duplicate_count = save_transactions(
            self.transactions,
            self.transaction_file,
            self.user_id,
            self.account
        )
        
        self.assertEqual(transaction_count, 2)
        self.assertEqual(duplicate_count, 0)
        self.assertEqual(mock_create_tx.call_count, 2)
        mock_update_file.assert_called_once_with(
            self.transaction_file.file_id,
            self.transaction_file.user_id,
            {'duplicate_count': 0}
        )

    @patch('services.file_processor_service.update_transaction_file')
    def test_update_file_status(self, mock_update_file):
        """Test file status update."""
        updated_file = TransactionFile(
            file_id=self.transaction_file.file_id,
            user_id=self.transaction_file.user_id,
            file_name=self.transaction_file.file_name,
            upload_date=self.transaction_file.upload_date,
            file_size=self.transaction_file.file_size,
            s3_key=self.transaction_file.s3_key,
            processing_status=ProcessingStatus.PROCESSED,
            transaction_count=2
        )
        mock_update_file.return_value = updated_file
        
        result = cast(TransactionFile, update_file_status(self.transaction_file, self.transactions))
        self.assertIsNotNone(result)
        self.assertEqual(result.processing_status, ProcessingStatus.PROCESSED)
        self.assertEqual(result.transaction_count, 2)
        mock_update_file.assert_called_once()

    @patch('services.file_processor_service.check_duplicate_transaction')
    def test_update_transaction_duplicates(self, mock_check_duplicate):
        """Test duplicate transaction detection."""
        mock_check_duplicate.side_effect = [True, False]
        
        duplicate_count = update_transaction_duplicates(self.transactions)
        self.assertEqual(duplicate_count, 1)
        self.assertEqual(self.transactions[0].status, "duplicate")
        self.assertEqual(self.transactions[1].status, "new")

    @patch('services.file_processor_service.get_transaction_by_account_and_hash')
    def test_determine_opening_balances_from_overlap(self, mock_get_tx):
        """Test opening balance determination from transaction overlap."""
        mock_tx = Transaction.create(
            account_id="test_account_id",
            user_id=self.user_id,
            file_id="test_file_id",
            date=int(datetime.now().timestamp() * 1000),
            description="Test Transaction",
            amount=Money(Decimal("-50.00"), Currency.USD),
            balance=Money(Decimal("950.00"), Currency.USD),
            import_order=1
        )
        mock_get_tx.return_value = mock_tx
        
        self.transactions[0].status = "duplicate"
        result = determine_opening_balances_from_transaction_overlap(self.transactions, Currency.USD)
        self.assertEqual(result, Money(Decimal("1000.00"), Currency.USD))

    @patch('services.file_processor_service.get_file_content')
    @patch('services.file_processor_service.create_transaction_file')
    @patch('services.file_processor_service.checked_optional_transaction_file')
    def test_process_new_file(self, mock_check_file, mock_create_file, mock_get_content):
        """Test new file processing."""
        mock_get_content.return_value = b"test content"
        mock_check_file.return_value = None  # Simulate a new file
        
        with patch('services.file_processor_service.process_new_file') as mock_process:
            mock_process.return_value = FileProcessorResponse(
                message="Success",
                transaction_count=2,
                duplicate_count=0,
                transactions=self.transactions
            )
            
            result = process_file(self.transaction_file)
            self.assertIsNotNone(result)
            self.assertEqual(result.transaction_count, 2)
            self.assertEqual(result.duplicate_count, 0)
            self.assertEqual(len(result.transactions or []), 2)
            
            # Verify auth check was called
            mock_check_file.assert_called_once_with(
                self.transaction_file.file_id,
                self.transaction_file.user_id
            )

    @patch('services.file_processor_service.get_file_content')
    @patch('services.file_processor_service.checked_mandatory_file_map')
    @patch('services.file_processor_service.checked_mandatory_account')
    @patch('services.file_processor_service.delete_transactions_for_file')
    @patch('utils.db_utils.get_transactions_table')
    @patch('utils.db_utils.get_files_table')
    def test_update_file_mapping(self, mock_get_files_table, mock_get_table, mock_delete, mock_check_account, mock_check_map, mock_get_content):
        """Test file mapping update."""
        # Mock the file map and account checks
        mock_check_map.return_value = self.file_map
        mock_check_account.return_value = self.account
        mock_get_content.return_value = b"test content"
        
        # Mock the transactions table
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table
        mock_table.query.return_value = {'Items': []}
        
        # Mock the files table
        mock_files_table = MagicMock()
        mock_get_files_table.return_value = mock_files_table
        mock_files_table.get_item.return_value = {'Item': self.transaction_file.to_dict()}
        mock_files_table.update_item.return_value = {}

        # Mock delete_transactions_for_file to return 1 deleted transaction
        mock_delete.return_value = 1
        
        # Test the update
        result = update_file_mapping(self.transaction_file)
        
        # Verify the result
        self.assertEqual(result.transaction_count, 0)
        self.assertEqual(result.duplicate_count, 0)
        
        # Verify the mocks were called
        mock_check_map.assert_called_once()
        mock_check_account.assert_called_once()


    @patch('services.file_processor_service.list_account_transactions')
    @patch('services.file_processor_service.list_account_files')
    @patch('services.file_processor_service.update_transaction')
    @patch('services.file_processor_service.update_transaction_file')
    @patch('services.file_processor_service.checked_mandatory_transaction_file')
    def test_update_opening_balance(self, mock_check_file, mock_update_file, mock_update_tx, mock_list_files, mock_list_tx):
        """Test opening balance update."""
        mock_list_tx.return_value = self.transactions
        mock_list_files.return_value = [self.transaction_file]
        mock_check_file.return_value = self.transaction_file
        mock_update_file.return_value = self.transaction_file
        
        new_balance = Money(Decimal("1100.00"), Currency.USD)
        self.transaction_file.opening_balance = new_balance
        
        result = update_opening_balance(self.transaction_file)
        self.assertEqual(result.transaction_count, 2)
        self.assertEqual(mock_update_tx.call_count, 2)
        mock_update_file.assert_called_once()
        mock_check_file.assert_called_once_with(
            self.transaction_file.file_id,
            self.transaction_file.user_id
        )

    @patch('services.file_processor_service.list_file_transactions')
    @patch('services.file_processor_service.update_transaction')
    @patch('services.file_processor_service.update_transaction_file')
    @patch('services.file_processor_service.checked_mandatory_transaction_file')
    def test_change_file_account(self, mock_check_file, mock_update_file, mock_update_tx, mock_list_tx):
        """Test file account change."""
        mock_list_tx.return_value = self.transactions
        mock_check_file.return_value = self.transaction_file
        
        new_account_id = "new_account_id"
        self.transaction_file.account_id = new_account_id
        
        with patch('services.file_processor_service.checked_mandatory_account') as mock_check_account:
            mock_check_account.return_value = self.account
            
            result = change_file_account(self.transaction_file)
            self.assertEqual(result.transaction_count, 2)
            mock_update_file.assert_called_once_with("test_file_id", self.user_id, {'account_id': new_account_id})
            self.assertEqual(mock_update_tx.call_count, 2)
            mock_check_file.assert_called_once_with(self.transaction_file.file_id, self.transaction_file.user_id) 